import sys
from contextlib import suppress
from threading import Event, Lock
from .util import call_sequence
from datetime import datetime, timedelta


MAX_CALL_DELAY = 2 #seconds


class FeatureAmpMixin(object):

    def __init__(self,*args,**xargs):
        super().__init__(*args,**xargs)
        self._pending = []
        self.features = {}
    
    def on_connect(self):
        for f in self.features.values(): f.unset()
        super().on_connect()
    
    def _set_feature_value(self, name, value):
        self.features[name].set(value)
    
    def on_receive_raw_data(self, data):
        super().on_receive_raw_data(data)
        consumed = {attrib:f.consume(data) for attrib,f in self.features.items() if f.matches(data)}
        if not consumed: self.on_change(None, data)
        for attr,(old,new) in consumed.items():
            if old == new: continue 
            if self.verbose > 4 and self._pending: print("[%s] %d pending functions"
                %(self.__class__.__name__, len(self._pending)), file=sys.stderr)
            if not any([p.has_polled(attr) for p in self._pending]):
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
    class InitMixin(object):
        """ apply @features to Amp """
        def __init__(self, *args, **xargs):
            super().__init__(*args,**xargs)
            for k,v in features.items(): v(self,k)
            
    dict_ = dict()
    try: dict_["protocol"] = sys._getframe(2).f_globals['__name__']
    except: pass
    dict_.update({
        k:property(
            lambda self,k=k:self.features[k].get(),
            lambda self,val,k=k:self._set_feature_value(k,val)
        )
        for k,v in features.items()
    })
    cls = type("AmpFeatures", (SendOnceMixin,InitMixin,FeatureAmpMixin), dict_)
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
                %(self.__class__.__name__,e,self._func.__name__), file=sys.stderr)
        self.missing_features = list(filter(lambda f:not f.isset(), self._features))
        if self._try_call(): return
        self.amp._pending.append(self) # = self.enable
        try: [f.async_poll() for f in self.missing_features]
        except ConnectionError: self.disable()
        
    def disable(self):
        with suppress(ValueError): self.amp._pending.remove(self)
        
    def _try_call(self):
        if not self.missing_features: return self._func(*self._args,**self._kwargs) or True
        
    def has_polled(self, feature):
        """ returns if we are waiting for @feature, update internal values and try call """
        try: self.missing_features.remove(self.amp.features.get(feature))
        except ValueError: return False
    
        if self._time+timedelta(seconds=MAX_CALL_DELAY) < datetime.now():
            if self.amp.verbose > 3: print("[%s] pending function `%s` expired"
                %(self.__class__.__name__, self._func.__name__), file=sys.stderr)
            self.disable()
        elif self._try_call():
            if self.amp.verbose > 4: print("[%s] called pending function %s"
                %(self.__class__.__name__,self._func.__name__), file=sys.stderr)
            self.disable()
        return True
        
    def _find_amp(self, args): 
        """ search FeatureAmpMixin type in args """
        try:
            amp = getattr(args[0],"amp",None)
            return next(filter(lambda e: isinstance(e,FeatureAmpMixin), (amp,)+args))
        except (StopIteration, IndexError):
            print("[WARNING] `%s` will never be called. @require needs "
                "FeatureAmpMixin instance"%self._func.__name__, file=sys.stderr)


class AbstractFeature(object):
    call = None
    default_value = None #if no response
    
    def matches(self, cmd):
        """ return True if cmd shall be parsed with this class """
        raise NotImplementedError()
        
    def parse(self, cmd): # rename to decodeVal?
        """ transform string @cmd to native value """
        raise NotImplementedError()
        
    def send(self, value):
        """ send @value to amp """
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
        require(self.attr)(lambda self: e.set())(self)
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

    def __init__(self, amp, attr):
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
    
    def set(self, value): self.send(value)

    def isset(self): return hasattr(self,'_val')
        
    def unset(self): self.__dict__.pop("_val",None); self._polled = False
    
    def async_poll(self):
        if self._polled: return
        self._polled = True
        return self.amp.send(self.call)
    
    def resend(self): return self.send(self._val)
    
    def consume(self, cmd):
        """ parse and apply @cmd to this object """
        return self.store(self.parse(cmd))
        
    def store(self, value):
        old = getattr(self,'_val',None)
        self._val = value
        if self._val != old: self.on_change(old, self._val)
        return old, self._val


class Feature(SynchronousFeatureMixin, AsyncFeature): pass


class RawFeature(Feature): # TODO: move to protocol.raw_telnet
    
    def parse(self, cmd): return cmd
    def send(self, value): self.amp.send(value)
    def matches(self, cmd): return False
    

def make_feature(amp, cmd, matches=None):
    return type(cmd, (RawFeature,), dict(call=cmd, matches=lambda self,cmd:matches(cmd)))(amp)


