import sys, traceback
from contextlib import suppress
from threading import Event, Lock
from .util import call_sequence
from datetime import datetime, timedelta


MAX_CALL_DELAY = 2 #seconds, max delay for calling function using "@require"


class FeatureAmpMixin(object):

    def __init__(self,*args,**xargs):
        self._pending = []
        self.features = {}
        # apply @features to Amp
        for attr,F in self._feature_classes.items(): F(self,attr)
        super().__init__(*args,**xargs)
    
    def on_connect(self):
        for f in self.features.values(): f.unset()
        def preload(amp): pass
        for f in set(self.preload_features): f not in self.features or require(f)(preload)(self)
        super().on_connect()
    
    def _set_feature_value(self, name, value):
        self.features[name].set(value)
    
    def mainloop_hook(self):
        super().mainloop_hook()
        for p in self._pending: p.check_expiration()
    
    def on_receive_raw_data(self, data):
        super().on_receive_raw_data(data)
        consumed = {attrib:f.consume(data) for attrib,f in self.features.items() if f.matches(data)}
        if not consumed: self.on_change(None, data)
        for attr,(old,new) in consumed.items():
            if old == new: continue 
            if self.verbose > 5 and self._pending: print("[%s] %d pending functions"
                %(self.__class__.__name__, len(self._pending)), file=sys.stderr)
            if not any([p.has_polled(attr) for p in self._pending.copy()]): # has_polled() changes self._pending
                self.on_change(attr, new)


class SendOnceMixin(object):
    """ prevent the same values from being sent to the amp in a row """

    def __init__(self,*args,**xargs):
        self._block_on_set = {}
        super().__init__(*args,**xargs)
        
    def _set_feature_value(self, name, value):
        if name in self._block_on_set and self._block_on_set[name] == value:
            return
        self._block_on_set[name] = value
        super()._set_feature_value(name,value)
        
    def on_change(self,*args,**xargs):
        self._block_on_set.clear() # unblock values after amp switches on
        super().on_change(*args,**xargs)
    
        
def make_features_mixin(**features):
    """
    Make a class where all attributes are getters and setters for amp properties
    args: class_attribute_name=MyFeature
        where MyFeature inherits from Feature
    """
    dict_ = {
        k:property(
            lambda self,k=k:self.features[k].get(),
            lambda self,val,k=k:self._set_feature_value(k,val)
        )
        for k,v in features.items()
    }
    dict_["_feature_classes"] = features
    cls = type("AmpFeatures", (SendOnceMixin,FeatureAmpMixin), dict_)
    return cls


def require(*features):
    """
    Decorator that states which amp features have to be loaded before calling the function.
    Call might be delayed until the feature values have been set.
    Can be used in Amp or AmpEvents.
    Example: @require("volume","muted")
    """
    return lambda func: lambda *args,**xargs: FunctionCall(features, func, args, xargs)


class FunctionCall(object):
    """ Function call that requires features """

    def __init__(self, features, func, args=set(), kwargs={}):
        self._func = func
        self._args = args
        self._kwargs = kwargs
        self._time = datetime.now()
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
        
    def _try_call(self):
        if not self.missing_features: return self._func(*self._args,**self._kwargs) or True
        
    def _find_amp(self, args): 
        """ search FeatureAmpMixin type in args """
        try:
            amp = getattr(args[0],"amp",None)
            return next(filter(lambda e: isinstance(e,FeatureAmpMixin), (amp,)+args))
        except (StopIteration, IndexError):
            print("[WARNING] `%s` will never be called. @require needs "
                "FeatureAmpMixin instance"%self._func.__name__, file=sys.stderr)

    def cancel(self):
        with suppress(ValueError): self.amp._pending.remove(self)
        
    def check_expiration(self):
        if self._time+timedelta(seconds=MAX_CALL_DELAY) < datetime.now():
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
        

class AbstractFeature(object):
    call = None
    default_value = None #if no response
    type = object # value data type, e.g. int, bool, str
    
    def matches(self, cmd):
        """ return True if cmd shall be parsed with this class """
        raise NotImplementedError()
        
    def decode(self, cmd):
        """ transform string @cmd to native value """
        raise NotImplementedError()
        
    def encode(self, value):
        """ encode @value to amp command """
        raise NotImplementedError()
    
    def on_change(self, old, new): pass


class SynchronousFeatureMixin(object):

    def __init__(self,*args,**xargs):
        self._poll_lock = Lock()
        super().__init__(*args,**xargs)

    def get(self):
        self._poll_lock.acquire()
        try:
            try: return super().get()
            except AttributeError:
                self.poll()
                return self._val
        finally: self._poll_lock.release()
        
    def poll(self):
        """ synchronous poll """
        e = Event()
        def poll_event(self): e.set()
        require(self.attr)(poll_event)(self)
        self.async_poll()
        if not e.wait(timeout=MAX_CALL_DELAY):
            if self.default_value: return self.store(self.default_value)
            else: raise ConnectionError("Timeout on waiting for answer for %s"%self.__class__.__name__)
        else: return self._val
    

class AsyncFeature(AbstractFeature):
    """
    An attribute of the amplifier
    High level telnet protocol communication
    """

    def __init__(self, amp, attr=None):
        """ amp instance, connected amp attribute name """
        super().__init__()
        self.amp = amp
        self.attr = attr
        self._polled = False
        amp.features[attr] = self
        
    name = property(lambda self:self.__class__.__name__)

    def get(self):
        if not self.amp.connected: 
            raise ConnectionError("`%s` is not available when amp is disconnected."%self.__class__.__name__)
        try: return self._val
        except AttributeError: 
            raise AttributeError("`%s` not available. Use @require"%self.attr)
    
    def set(self, value, force=False):
        if not force and not isinstance(value, self.type):
            raise TypeError("Value `%s` is not of type `%s`."%(value,self.type.__name__))
        self.amp.send(self.encode(value))

    def isset(self): return hasattr(self,'_val')
        
    def unset(self): self.__dict__.pop("_val",None); self._polled = False
    
    def async_poll(self):
        if self._polled: return
        self._polled = True
        return self.amp.send(self.call)
    
    def resend(self): return self.set(self._val)
    
    def consume(self, cmd):
        """ decode and apply @cmd to this object """
        try: d = self.decode(cmd)
        except: print(traceback.format_exc(), file=sys.stderr)
        else: return self.store(d)
        
    def store(self, value):
        old = getattr(self,'_val',None)
        self._val = value
        if self._val != old: self.on_change(old, self._val)
        return old, self._val


class Feature(SynchronousFeatureMixin, AsyncFeature): pass

class NumericFeature(Feature):
    min=0
    max=99


class BoolFeature(Feature): type=bool

class IntFeature(NumericFeature): type=int

class SelectFeature(Feature):
    type=str
    options = []

    def set(self, value, force=False):
        if not force and value not in self.options:
            raise ValueError("Value must be one of %s or try amp.features[%s].set(value, force=True)"
                %(self.options, repr(self.attr)))
        return super().set(value, force)
    

class FloatFeature(NumericFeature):
    type=float
    
    def set(self, value, force=False):
        return super().set((float(value) if isinstance(value, int) else value), force)


