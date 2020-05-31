class AbstractFeature(object):
    function_call = None
    default_value = None #if no response
    
    def matches(self, cmd): raise NotImplementedError()
    def consume(self, cmd): raise NotImplementedError()
    def send(self, value=None): raise NotImplementedError()
    def on_change(self, old, new): pass


class Feature(AbstractFeature):
    # alternatives:
    #    move all features to denon.__init__() -setter
    #    no __get__ but __str__ and __int__ and __bool__ -setter

    #    catch with __getattribute__ in Denon.feature -doppelung von objekten in .features wegen __get__ -wegen klassenvariable: alle funktionen brauchen instanz als arg
    #    stay with __get__ and switch to class attribute, no instance attribute -only one avr possible +comfort
    #    Denon.feature is object with __getattr__ -no autocomplete
    # poll, send, consume zu Denon verschieben?

    def __init__(self, amp):
        self.amp = amp

    def get(self):
        if not self.amp.connected: 
            raise ConnectionError("`%s` is not available when amp is disconnected."%self.__class__.__name__)
        try: return self._val
        except AttributeError:
            self.poll()
            return self._val
        
    def set(self, value):
        if getattr(self, "_val", None) == value: return
        #self._val = value
        self.send(value)

    def isset(self):
        return hasattr(self,'_val')
        
    def unset(self): self.__dict__.pop("_val",None)
        
    def poll(self):
        try: cmd = self.amp(self.function_call, matches=self.matches)
        except RuntimeError: return self.store(self.default_value)
        else: return self.consume(cmd)
        
    def store(self, value):
        old = getattr(self,'_val',None)
        self._val = value
        if self._val != old: self.on_change(old, self._val)
        return old, self._val

