import sys
from threading import Event, Lock
from .util import call_sequence
from datetime import datetime, timedelta


MAX_CALL_DELAY = 2 #seconds


def require(*features):
    """
    Decorator that states which amp features have to be loaded before calling the function.
    Call might be delayed until the feature values have been set.
    Can be used in types RequirementsAmpMixin or AmpEvents.
    Example: @require("volume","muted")
    """
    return lambda func: lambda *args,**xargs: FunctionCall(features, func, args, xargs)


class RequirementsAmpMixin(object):

    def __init__(self,*args,**xargs):
        self._pending = []
        self.mainloop = call_sequence(self.mainloop_prepare, self.mainloop)
        super().__init__(*args,**xargs)

    def mainloop_prepare(self,*args,**xargs):
        if hasattr(self,"_on_change"): return
        self._on_change = self.on_change
        self.on_change = self.on_change_decorator
    
    def on_change_decorator(self, attr, val):
        """ update and call methods with @require decorator """
        if self.verbose > 4 and self._pending: print("[%s] %d pending functions"
            %(self.__class__.__name__, len(self._pending)), file=sys.stderr)
        if not any([p.has_polled(attr) for p in self._pending]):
            self._on_change(attr, val)


class FunctionCall(object):
    """ Function that requires features """

    def __init__(self, features, func, args=set(), kwargs={}):
        self._func = func
        self._args = args
        self._kwargs = kwargs
        self._time = datetime.now()
        self.amp = self._find_amp(args)
        self.amp._pending.append(self)
        try:
            assert(self.amp.connected and hasattr(self.amp,"features"))
            self._features = [self.amp.features[name] for name in features]
            self._polled = self.missing_features
            for f in self._polled: f.async_poll()
        except (AssertionError, AttributeError, KeyError, ConnectionError): 
            try: self.amp._pending.remove(self)
            except ValueError: pass
        else: self._try_call()
        
    def _try_call(self):
        if not self.missing_features:
            self.amp._pending.remove(self)
            self._func(*self._args,**self._kwargs)
            return True
        
    def has_polled(self, feature):
        if self._time+timedelta(seconds=MAX_CALL_DELAY) < datetime.now():
            self.amp._pending.remove(self)
            if self.amp.verbose > 3: print("[%s] pending function `%s` expired"
                %(self.__class__.__name__, self._func.__name__), file=sys.stderr)
        elif self._try_call() and self.amp.verbose > 4:
            print("[%s] called pending function %s"
                %(self.__class__.__name__,self._func.__name__), file=sys.stderr)

        try: self._polled.remove(self.amp.features.get(feature))
        except ValueError: return False
        else: return True
    
    @property
    def missing_features(self): return list(filter(lambda f:not f.isset(), self._features))

    def _find_amp(self, args): 
        """ search RequirementsAmpMixin type in args """
        try:
            amp = getattr(args[0],"amp",None)
            return next(filter(lambda e: isinstance(e,RequirementsAmpMixin), (amp,)+args))
        except (StopIteration, IndexError):
            raise TypeError("@require needs RequirementsAmpMixin instance")


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
        
    def unset(self): self.__dict__.pop("_val",None)
    
    def async_poll(self): return self.amp.send(self.call)
    
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


