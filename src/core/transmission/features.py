import sys, traceback, re, math
from contextlib import suppress
from decimal import Decimal
from threading import Event, Lock, Timer, Thread
from datetime import datetime, timedelta
from ..util import call_sequence, Bindable, AttrDict
from ..config import config
from .types import ClientType, ServerType


MAX_CALL_DELAY = 2 #seconds, max delay for calling function using "@require"


class FunctionCall(object):
    """ Function call that requires features. Drops call if no connection """

    def __init__(self, target, func, args=tuple(), kwargs={}, features=tuple(), timeout=MAX_CALL_DELAY):
        self._lock = Lock()
        self._target = target
        self._func = func
        self._args = args
        self._kwargs = kwargs
        self._missing_features = features
        self._timeout = datetime.now()+timedelta(seconds=timeout) if timeout != None else None
        self.postpone()
        if not self._try_call():
            try: [f.async_poll() for f in self._missing_features]
            except ConnectionError: self.cancel()

    def __repr__(self): return "<pending%s>"%self._func
    
    def _try_call(self):
        with self._lock:
            if not self.active: return False
            self._missing_features = list(filter(lambda f:not f.isset(), self._missing_features))
            if not self._missing_features:
                try: self._func(*self._args, **self._kwargs)
                except ConnectionError: pass
                self.cancel()
                return True

    def postpone(self): self._target._pending.append(self)

    def cancel(self):
        with suppress(ValueError): self._target._pending.remove(self)

    active = property(lambda self: self in self._target._pending)

    expired = property(lambda self: self._timeout and self._timeout < datetime.now())

    def check_expiration(self):
        if self.expired and self._target.verbose > 1:
            print("[%s] pending function `%s` expired"
                %(self.__class__.__name__, self._func.__name__), file=sys.stderr)
            self.cancel()
    
    def on_feature_set(self, feature):
        if feature in self._missing_features and self._try_call():
            if self._target.verbose > 5: print("[%s] called pending function %s"
                %(self.__class__.__name__, self._func.__name__), file=sys.stderr)


class Features(AttrDict):
    
    def wait_for(self, *features):
        try: features = [f if isinstance(f, Feature) else self[f] for f in features]
        except KeyError as e:
            print(f"[{self.__class__.__name__}] Warning: Target does not provide feature. {e}",
                file=sys.stderr)
            return False
        threads = [Thread(target=f.wait_poll, daemon=True, name="wait_for") for f in features]
        for t in threads: t.start()
        for t in threads: t.join()
        return all([f.isset() for f in features])
        

class FeatureInterface(object):
    name = "Short description"
    category = "Misc"
    call = None # for retrieval, call target.send(call)
    default_value = None # if no response from server
    dummy_value = None # for dummy server
    type = object # value data type, e.g. int, bool, str
    #key = "key" # feature will be available as target.key; default: key = class name

    def init_on_server(self):
        """ called after __init__ on server side """
        pass

    def poll_on_server(self):
        """ This is being executed on server side when the client asks for a value
        and must call self.set(some value) """
        raise NotImplementedError()
    
    def set_on_server(self, value):
        """ This is being executed on server side when the client tries to set a value.
        It shall call self.set(value) """
        raise NotImplementedError()
    
    def matches(self, data):
        """
        @data: line received from target
        return True if data shall be parsed with this class
        """
        raise NotImplementedError()
        
    def serialize(self, value):
        """ transform @value to string """
        raise NotImplementedError()

    def unserialize(self, data):
        """ transform string @data to type self.type """
        raise NotImplementedError()


class _MetaFeature(type):

    def __init__(cls, name, bases, dct):
        if "key" not in dct:
            cls.key = re.sub(r'(?<!^)(?=[A-Z])', '_', cls.__name__).lower()
        if "name" not in dct:
            cls.name = re.sub(r'(?<!^)(?=[A-Z])', ' ', cls.__name__)
            cls.name = " ".join(["%s%s"%(x[0].upper(),x[1:]) if len(x)>0 else "" for x in cls.name.split("_")])

        
class AsyncFeature(FeatureInterface, Bindable, metaclass=_MetaFeature):
    """
    A target attribute for high level communication
    
    Warning: Calling get() in the event callbacks can cause deadlocks.
        Instead, get the value from the function parameter.
    """
    _val = None
    _prev_val = None
    _block_on_send = None
    _block_on_send_resetter = None

    def __init__(self, target):
        super().__init__()
        target_type = (ServerType, ClientType)
        if not any([isinstance(target, c) for c in target_type]):
            raise TypeError("target must inherit one of %s."%(", ".join(map(lambda c:c.__name__, target_type))))
        self.target = target
        self._lock = Lock()
        self._event_on_set = Event()
        target.features[self.key] = self
        
    name = property(lambda self:self.__class__.__name__)
    
    def __str__(self): return str(self.get()) if self.isset() else "..."
    
    def get(self):
        if not self.isset(): raise AttributeError(f"`{self.key}` not available. Use Target.schedule")
        else: return self._val
    
    def send(self, value, force=False):
        """ request update to @value on other side """
        assert(value is not None)
        if not force and not isinstance(value, self.type):
            print("WARNING: Value %s is not of type %s."%(repr(value),self.type.__name__), file=sys.stderr)
        serialized = self.serialize(self.type(value))
        if not self._blocked(serialized): self.target.send(serialized)

    @classmethod
    def _blocked(cls, serialized):
        """ prevent sending the same line many times """
        if cls._block_on_send == serialized: return True
        cls._block_on_send = serialized
        try: cls._block_on_send_resetter.cancel()
        except AttributeError: pass
        cls._block_on_send_resetter = Timer(1, lambda: setattr(cls, "_block_on_send", None))
        cls._block_on_send_resetter.start()
    
    def isset(self): return self._val != None
        
    def unset(self):
        with self._lock:
            self._val = None
            self.on_unset()
        #with suppress(ValueError): self.target._polled.remove(self.call)

    def async_poll(self, *args, **xargs): self.target.poll_feature(self, *args, **xargs)
    
    def poll_on_client(self):
        """ async_poll() executed on client side """
        if self.default_value is not None:
            self._timer_set_default = Timer(MAX_CALL_DELAY, self._set_default)
            self._timer_set_default.start()
        if self.call is not None: self.target.send(self.call)
    
    def poll_on_dummy(self):
        if self.default_value is not None: val = self.default_value
        elif self.dummy_value is not None: val = self.dummy_value
        else: raise ValueError("Feature type %s has no dummy value."%f)
        #self.on_receive_raw_data(f.serialize(val)) # TODO: handle cases where f.call matches but f.matches() is False and maybe f'.matches() is True
        self.set(val)

    def _set_default(self):
        with self._lock:
            if not self.isset(): self._set(self.default_value)
    
    def resend(self): return AsyncFeature.send(self, self._val, force=True)
    
    def consume(self, cmd):
        """ unserialize and apply @cmd to this object """
        self.__class__._block_on_send = None # for power.consume("PWON")
        try: d = self.unserialize(cmd)
        except: print(traceback.format_exc(), file=sys.stderr)
        else: return self.target.set_feature(self, d)
        
    def set(self, value):
        with self._lock: return self._set(value)
    
    def _set(self, value):
        assert(value is not None)
        self._prev_val = self._val
        self._val = value
        if not self.isset(): return
        if self._val != self._prev_val: self.on_change(self._val)
        if self._prev_val == None: self.on_set()
        self.on_processed(value)
        return self._prev_val, self._val

    def bind(self, on_change=None, on_set=None, on_unset=None, on_processed=None):
        """ Register an observer with bind() and call the callback as soon as possible
        to stay synchronised """
        with self._lock:
            if self.isset():
                if on_change: on_change(self.get())
                if on_set: on_set()
                if on_processed: on_processed(self.get())
            elif on_unset: on_unset()
            
            if on_change: super().bind(on_change = on_change)
            if on_set: super().bind(on_set = on_set)
            if on_unset: super().bind(on_unset = on_unset)
            if on_processed: super().bind(on_processed = on_processed)
            
    def on_change(self, val):
        """ This event is being called when self.options or the return value of self.get() changes """
        self.target.on_feature_change(self.key, val)
    
    def on_set(self):
        """ Event is fired on initial set """
        try: self._timer_set_default.cancel()
        except: pass
        self._event_on_set.set()
        if getattr(self.target, "_pending", None):
            if self.target.verbose > 5: print("[%s] %d pending functions"
                %(self.target.__class__.__name__, len(self.target._pending)), file=sys.stderr)
            if self.target.verbose > 6: print("[%s] pending functions: %s"
                %(self.target.__class__.__name__, self.target._pending), file=sys.stderr)
            for call in self.target._pending.copy(): # on_feature_set() changes _pending
                call.on_feature_set(self)
        
    def on_unset(self):
        try: self._timer_set_default.cancel()
        except: pass
        self._event_on_set.clear()
    
    def on_processed(self, value):
        """ This event is being called each time the feature is being set to a value
        even if the value is the same as the previous one """
        pass


class SynchronousFeature(AsyncFeature):

    def __init__(self,*args,**xargs):
        self._poll_lock = Lock()
        super().__init__(*args,**xargs)

    def get(self):
        with self._poll_lock:
            try: return super().get()
            except AttributeError:
                if self.wait_poll(): return super().get()
                else: raise ConnectionError("Timeout on waiting for answer for %s"%self.__class__.__name__)

    def wait_poll(self, force=False):
        """ Poll and wait if Feature is unset. Returns False on timeout and True otherwise """
        if not self.target.connected: return False
        if force: self.unset()
        if not self.isset():
            try: self.async_poll(force)
            except ConnectionError: return False
            if not self._event_on_set.wait(timeout=MAX_CALL_DELAY+.1): return False
        return True


Feature = SynchronousFeature

class NumericFeature(Feature):
    min=0
    max=99


class IntFeature(NumericFeature):
    type=int
    dummy_value = property(lambda self: math.ceil((self.max+self.min)/2))


class SelectFeature(Feature):
    type=str
    options = []
    dummy_value = property(lambda self: self.options[0] if self.options else "?")

    def send(self, value, force=False):
        if not force and value not in self.options:
            raise ValueError("Value must be one of %s or try target.features.%s.send(value, force=True)"
                %(self.options, self.key))
        return super().send(value, force)
    

class BoolFeature(SelectFeature):
    type=bool
    options = [True, False]
    dummy_value = False


class DecimalFeature(NumericFeature):
    type=Decimal
    dummy_value = property(lambda self: Decimal(self.max+self.min)/2)
    
    def send(self, value, force=False):
        return super().send((Decimal(value) if isinstance(value, int) else value), force)


class PresetValueMixin:
    """ Inherit if feature value shall have a preset value. Set value in inherited class. """
    value = None

    def __init__(self,*args,**xargs):
        super().__init__(*args,**xargs)
        self._val = self.value
    def unset(self): self._val = self.value


class ConstantValueMixin(PresetValueMixin):
    """ Inerhit if feature value may not change """
    def matches(self,*args,**xargs): return False
    def set(self,*args,**xargs): pass


class ClientToServerFeatureMixin:
    """ Inheriting features are write only on client and read only on server """
    call = None

    def __init__(self, *args, **xargs):
        super().__init__(*args, **xargs)
        if isinstance(self.target, ClientType): self.target.bind(on_connect=self.on_set)

    # for client
    def get(self): return "(select)" if isinstance(self.target, ClientType) else super().get()
    def isset(self):
        return self.target.connected if isinstance(self.target, ClientType) else super().isset()

    # for server
    def send(self, *args, **xargs):
        if isinstance(self.target, ClientType): return super().send(*args, **xargs)
        else: raise ValueError("This is a unidirectional feature")

    def resend(self): isinstance(self.target, ClientType) and super().resend()


class MultipartFeatureMixin:
    """ This mixin allows you to send and receive a value in multiple parts. The parts are a
    list. Implement the conversion of the value to and from a list in to_parts() and from_parts(). 
    In Telnet, parts could be rows. """
    SEPARATOR = "\r"
    TERMINATOR = "END"

    def __init__(self, *args, **xargs):
        super().__init__(*args, **xargs)
        self._buffer = []

    def to_parts(self, value):
        """ value is of type self.type. Returns a list of string """
        raise NotImplementedError()

    def from_parts(self, l):
        """ l is of type list. Returns object of type self.type """
        raise NotImplementedError()

    def serialize(self, value):
        return self.SEPARATOR.join([super(MultipartFeatureMixin, self).serialize(e)
            for e in [*self.to_parts(value), self.TERMINATOR]])

    def unserialize(self, data):
        # will return one element on telnet and at least one on plain_emulator
        return [super(MultipartFeatureMixin, self).unserialize(e) for e in data.split(self.SEPARATOR)]

    def set(self, l):
        if l in (self.dummy_value, self.default_value): return super().set(l)
        for line in l:
            if line == self.TERMINATOR:
                super().set(self.from_parts(self._buffer)) # cause self.on_change()
                self._buffer.clear()
            else: self._buffer.append(line)


