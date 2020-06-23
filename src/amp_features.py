from threading import Event, Lock
from .amp import require, RESPONSE_TIMEOUT


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


class SynchronousMixin(object):

    def __init__(self):
        self._poll_lock = Lock()
        super().__init__()

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
        require(self.attr)(e.set)()
        self.async_poll()
        if not e.wait(timeout=RESPONSE_TIMEOUT):
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
        except AttributeError: raise AttributeError("Value not available. Use @require")
    
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


Feature(SynchronousMixin, AsyncFeature): pass


class RawFeature(Feature): # TODO: move to protocol.raw_telnet
    
    def parse(self, cmd): return cmd
    def send(self, value): self.amp.send(value)
    def matches(self, cmd): return False
    

def make_feature(amp, cmd, matches=None):
    return type(cmd, (RawFeature,), dict(call=cmd, matches=lambda self,cmd:matches(cmd)))(amp)


