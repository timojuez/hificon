import sys, traceback, re
from contextlib import suppress
from decimal import Decimal
from threading import Event, Lock, Timer, Thread
from datetime import datetime, timedelta
from ..util import call_sequence, Bindable, AttrDict
from ..config import config
from .protocol_type import ProtocolType


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
    default_value = None #if no response
    type = object # value data type, e.g. int, bool, str
    #key = "key" # feature will be available as target.key; default: key = class name
    
    def poll_on_server(self):
        """ This is being executed on server side and must call self.store(some value) """
        raise NotImplementedError()
    
    def matches(self, data):
        """
        @data: line received from target
        return True if data shall be parsed with this class
        """
        raise NotImplementedError()
        
    def decode(self, data):
        """ transform string @data to type self.type """
        raise NotImplementedError()
        
    def encode(self, value):
        """ encode @value to target command """
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
    """
    _val = None
    _block_on_send = None
    _block_on_send_resetter = None

    def __init__(self, target):
        super().__init__()
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
        assert(value is not None)
        if not force and not isinstance(value, self.type):
            print("WARNING: Value %s is not of type %s."%(repr(value),self.type.__name__), file=sys.stderr)
        encoded = self.encode(self.type(value))
        if not self._blocked(encoded): self.target.send(encoded)

    @classmethod
    def _blocked(cls, encoded):
        """ prevent sending the same line many times """
        if cls._block_on_send == encoded: return True
        cls._block_on_send = encoded
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
            self._timer_store_default = Timer(MAX_CALL_DELAY, self._store_default)
            self._timer_store_default.start()
        if self.call is not None: self.target.send(self.call)
    
    def _store_default(self):
        with self._lock:
            if not self.isset(): self._store(self.default_value)
    
    def resend(self): return AsyncFeature.send(self, self._val, force=True)
    
    def consume(self, cmd):
        """ decode and apply @cmd to this object """
        self.__class__._block_on_send = None # for power.consume("PWON")
        try: d = self.decode(cmd)
        except: print(traceback.format_exc(), file=sys.stderr)
        else: return self.store(d)
        
    def store(self, value):
        with self._lock: return self._store(value)
    
    def _store(self, value):
        assert(value is not None)
        old = self._val
        self._val = value
        if not self.isset(): return
        if self._val != old: self.on_change(old, self._val)
        if old == None: self.on_set()
        self.on_store(value)
        return old, self._val

    def bind(self, on_change=None, on_set=None, on_unset=None, on_store=None):
        """ Register an observer with bind() and call the callback as soon as possible
        to stay synchronised """
        with self._lock:
            if self.isset():
                if on_change: on_change(self.get())
                if on_set: on_set()
                if on_store: on_store(self.get())
            elif on_unset: on_unset()
            
            if on_change: super().bind(on_change = lambda old, new: on_change(new))
            if on_set: super().bind(on_set = on_set)
            if on_unset: super().bind(on_unset = on_unset)
            if on_store: super().bind(on_store = on_store)
            
    def on_change(self, old, new):
        """ This event is being called when self.options or the return value of self.get() changes """
        self.target.on_feature_change(self.key, new, old)
    
    def on_set(self):
        """ Event is fired on initial set """
        try: self._timer_store_default.cancel()
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
        try: self._timer_store_default.cancel()
        except: pass
        self._event_on_set.clear()
    
    def on_store(self, value):
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


class IntFeature(NumericFeature): type=int

class SelectFeature(Feature):
    type=str
    options = []

    def send(self, value, force=False):
        if not force and value not in self.options:
            raise ValueError("Value must be one of %s or try target.features.%s.send(value, force=True)"
                %(self.options, self.key))
        return super().send(value, force)
    

class BoolFeature(SelectFeature):
    type=bool
    options = [True, False]


class DecimalFeature(NumericFeature):
    type=Decimal
    
    def send(self, value, force=False):
        return super().send((Decimal(value) if isinstance(value, int) else value), force)


class PresetValue:
    """ Inherit if feature value shall have a preset value. Set value in inherited class. """
    value = None

    def __init__(self,*args,**xargs):
        super().__init__(*args,**xargs)
        self._val = self.value
    def unset(self): self._val = self.value


class Constant(PresetValue):
    """ Inerhit if feature value may not change """
    def matches(self,*args,**xargs): return False
    def store(self,*args,**xargs): pass


