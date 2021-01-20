import sys, traceback, re
from contextlib import suppress
from decimal import Decimal
from threading import Event, Lock, Timer
from datetime import datetime, timedelta
from ..util import call_sequence, Bindable
from ..common.config import config
from .amp_type import AmpType


MAX_CALL_DELAY = 2 #seconds, max delay for calling function using "@require"


def require(*features, timeout=MAX_CALL_DELAY):
    """
    Decorator that states which features have to be loaded before calling the function.
    Call might be delayed until the feature values have been set.
    Skip call if delay is longer than @timeout seconds.
    Can be used in Amp or AmpEvents.
    Example: @require("volume","muted")
    """
    return lambda func: lambda *args,**xargs: FunctionCall(features, func, args, xargs, timeout)


class FunctionCall(object):
    """ Function call that requires features. Drops call if no connection """

    def __init__(self, features, func, args=set(), kwargs={}, timeout=MAX_CALL_DELAY):
        self._func = func
        self._args = args
        self._kwargs = kwargs
        self._timeout = datetime.now()+timedelta(seconds=timeout) if timeout != None else None
        self.amp = self._find_amp(args)
        if not self.amp or not self.amp.connected: return
        try: self._features = [self.amp.features[name] for name in features]
        except KeyError as e:
            if self.amp.verbose > 3:
                print("[%s] Warning: Amp does not provide feature required by `%s`: %s"
                %(self.__class__.__name__,self._func.__name__,e), file=sys.stderr)
            return
        self.missing_features = list(filter(lambda f:not f.isset(), self._features))
        if self._try_call(): return
        self.amp._pending.append(self) #postpone
        try: [f.async_poll() for f in self.missing_features]
        except ConnectionError: self.cancel()
    
    def __repr__(self): return "<pending%s>"%self._func
    
    def _try_call(self):
        if not self.missing_features: 
            try: self._func(*self._args,**self._kwargs)
            except ConnectionError: self.cancel()
            return True
        
    def _find_amp(self, args): 
        """ search AmpType type in args """
        try:
            amp = getattr(args[0],"amp",None) # = self.amp if args==(self,)
            return next(filter(lambda e: isinstance(e,AmpType), (amp,)+args))
        except (StopIteration, IndexError):
            raise TypeError("`%s` cannot be called. @require needs "
                "AmpType instance as argument"%self._func.__name__)

    def cancel(self):
        with suppress(ValueError): self.amp._pending.remove(self)
        
    def check_expiration(self):
        if self._timeout and self._timeout < datetime.now():
            if self.amp.verbose > 1: print("[%s] pending function `%s` expired"
                %(self.__class__.__name__, self._func.__name__), file=sys.stderr)
            self.cancel()
    
    def has_polled(self, feature):
        """ returns if we are waiting for @feature, update internal values and try call """
        try: self.missing_features.remove(self.amp.features.get(feature))
        except ValueError: return False
        if self._try_call():
            if self.amp.verbose > 5: print("[%s] called pending function %s"
                %(self.__class__.__name__,self._func.__name__), file=sys.stderr)
            self.cancel()
        return True
        

class FeatureInterface(object):
    name = "Short description"
    category = "Misc"
    call = None # for retrieval, call amp.send(call)
    default_value = None #if no response
    type = object # value data type, e.g. int, bool, str
    #key = "key" # feature will be available as amp.key; default: key = class name
    
    def poll_on_server(self):
        """ This is being executed on server side and must call self.store(some value) """
        raise NotImplementedError()
    
    def matches(self, data):
        """
        @data: line received from amp
        return True if data shall be parsed with this class
        """
        raise NotImplementedError()
        
    def decode(self, data):
        """ transform string @data to type self.type """
        raise NotImplementedError()
        
    def encode(self, value):
        """ encode @value to amp command """
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
    An attribute of the amplifier
    High level telnet protocol communication
    """
    _val = None
    _block_on_send = None

    def __init__(self, amp):
        """ amp instance, connected amp attribute name """
        super().__init__()
        self.amp = amp
        self._lock = Lock()
        amp.features[self.key] = self
        
    name = property(lambda self:self.__class__.__name__)
    
    def __str__(self): return str(self.get()) if self.isset() else "..."
    
    def get(self):
        if not self.isset(): raise AttributeError("`%s` not available. Use @require"%self.key)
        else: return self._val
    
    def send(self, value, force=False):
        assert(value is not None)
        if not force and not isinstance(value, self.type):
            print("WARNING: Value %s is not of type %s."%(repr(value),self.type.__name__), file=sys.stderr)
        encoded = self.encode(self.type(value))
        if not force and self._block_on_send == encoded: return
        self._block_on_send = encoded
        self.amp.send(encoded)
    
    def isset(self): return self._val != None
        
    def unset(self):
        with self._lock:
            self._val = None
            self.on_unset()
        #with suppress(ValueError): self.amp._polled.remove(self.call)

    def async_poll(self, *args, **xargs): self.amp.poll_feature(self, *args, **xargs)
    
    def poll_on_client(self):
        """ async_poll() executed on client side """
        if self.default_value is not None:
            self._timer_store_default = Timer(MAX_CALL_DELAY, self._store_default)
            self._timer_store_default.start()
        self.amp.send(self.call)
    
    def _store_default(self):
        with self._lock:
            if not self.isset(): self._store(self.default_value)
    
    def resend(self): return AsyncFeature.send(self, self._val, force=True)
    
    def consume(self, cmd):
        """ decode and apply @cmd to this object """
        for f in self.amp.features.values(): f._block_on_send = None
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
        self.amp.on_feature_change(self.key, new, old)
    
    def on_set(self):
        """ Event is fired on initial set """
        try: self._timer_store_default.cancel()
        except: pass
        if getattr(self.amp, "_pending", None):
            if self.amp.verbose > 5: print("[%s] %d pending functions"
                %(self.amp.__class__.__name__, len(self.amp._pending)), file=sys.stderr)
            if self.amp.verbose > 6: print("[%s] pending functions: %s"
                %(self.amp.__class__.__name__, self.amp._pending), file=sys.stderr)
            for call in self.amp._pending.copy(): # has_polled() changes _pending
                call.has_polled(self.key)
        
    def on_unset(self):
        try: self._timer_store_default.cancel()
        except: pass
    
    def on_store(self, value):
        """ This event is being called each time the feature is being set to a value
        even if the value is the same as the previous one """
        pass


class SynchronousFeature(AsyncFeature):

    def __init__(self,*args,**xargs):
        self._poll_lock = Lock()
        super().__init__(*args,**xargs)

    def get(self):
        self._poll_lock.acquire()
        try:
            try: return super().get()
            except AttributeError:
                self.poll()
                return super().get()
        finally: self._poll_lock.release()
        
    def poll(self, force=False):
        """ synchronous poll """
        e = Event()
        def poll_event(self): e.set()
        require(self.key)(poll_event)(self)
        self.async_poll(force)
        if not e.wait(timeout=MAX_CALL_DELAY+.1):
            raise ConnectionError("Timeout on waiting for answer for %s"%self.__class__.__name__)
        return super().get()
    

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
            raise ValueError("Value must be one of %s or try amp.features.%s.send(value, force=True)"
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


