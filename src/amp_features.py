class AbstractFeature(object):
    call = None
    default_value = None #if no response
    
    def matches(self, cmd): raise NotImplementedError()
    def consume(self, cmd): raise NotImplementedError()
    def send(self, value=None): raise NotImplementedError()
    def on_change(self, old, new): pass


class Feature(AbstractFeature):
    """ An attribute of the amplifier """

    def __init__(self, amp):
        self.amp = amp
        
    name = property(lambda self:self.__class__.__name__)

    def get(self):
        if not self.amp.connected: 
            raise ConnectionError("`%s` is not available when amp is disconnected."%self.__class__.__name__)
        try: return self._val
        except AttributeError:
            self.poll()
            return self._val
        
    def set(self, value): self.send(value)

    def isset(self): return hasattr(self,'_val')
        
    def unset(self): self.__dict__.pop("_val",None)
        
    def poll(self):
        try: cmd = self.amp(self.call, matches=self.matches)
        except TimeoutError as e:
            if self.default_value: return self.store(self.default_value)
            else: raise ConnectionError(e)
        else: 
            return self.consume(cmd)
    
    def resend(self): return self.send(self._val)
    
    def store(self, value):
        old = getattr(self,'_val',None)
        self._val = value
        if self._val != old: self.on_change(old, self._val)
        return old, self._val

