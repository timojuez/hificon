class AbstractDenonFeature(object):
    function = ""
    translation = {}
    
    def decodeVal(self, val):
        return self.translation[val]
        
    def encodeVal(self, val):
        return {val:key for key,val in self.translation.items()}[val]


class DenonFeature(AbstractDenonFeature):
    # alternatives:
    #    move all features to denon.__init__() -setter
    #    no __get__ but __str__ and __int__ and __bool__ -setter

    #    catch with __getattribute__ in Denon.feature -doppelung von objekten in .features wegen __get__ -wegen klassenvariable: alle funktionen brauchen instanz als arg
    #    stay with __get__ and switch to class attribute, no instance attribute -only one avr possible +comfort
    #    Denon.feature is object with __getattr__ -no autocomplete
    # poll, send, consume zu Denon verschieben?

    def __init__(self, denon, name):
        self.denon = denon

    def get(self):
        if not self.denon.connected: 
            raise ConnectionError("`%s` is not available when AVR is disconnected."%self.__class__.__name__)
        try: return self._val
        except AttributeError:
            self._poll()
            return self._val
        
    def set(self, value):
        if getattr(self, "_val", None) == value: return
        #self._val = value
        self._send(value)

    def _isset(self):
        return hasattr(self,'_val')
        
    def _poll(self):
        return self._consume(self.denon("%s?"%self.function))
    
    def _send(self, value=None):
        if value is None: value = self._val
        cmd = "%s%s"%(self.function, self.encodeVal(value))
        self.denon(cmd)
    
    def _consume(self, cmd):
        """
        Update property according to @cmd
        """
        if not cmd.startswith(self.function): 
            raise ValueError("Cannot handle `%s`."%cmd)
        param = cmd[len(self.function):]
        old = getattr(self,'_val',None)
        self._val = self.decodeVal(param)
        return old, self._val
    

class DenonFeature_Volume(DenonFeature):
    function = "MV"
    # TODO: value may be relative?
    
    def _poll(self):
        # TODO: maybe switch to asynchronous and remove this function
        return self._consume(self.denon("MV?",ret=lambda s:
            s.startswith("MV") and s[2] != "M"))
    
    def set(self, value):
        super(DenonFeature_Volume,self).set(self._roundVolume(value))
        
    @staticmethod
    def _roundVolume(vol):
        return .5*round(vol/.5)

    def decodeVal(self, val):
        return int(val.ljust(3,"0"))/10
        
    def encodeVal(self, val):
        return "%03d"%(val*10)
        
        
class DenonFeature_Maxvol(DenonFeature_Volume):
    function="MVMAX "
    
    def _poll(self):
        cmd = self.denon("MV?", ret=self.function)
        if cmd: return self._consume(cmd)
        old = getattr(self,'_val',None)
        self._val = 98
        return old, self._val
        
    def encodeVal(self, val):
        raise RuntimeError("Cannot set MVMAX!")
        
    def _send(self): pass
        

class DenonFeature_Power(DenonFeature):
    function = "PW"
    translation = {"ON":True,"STANDBY":False}
    
    
class DenonFeature_Muted(DenonFeature):
    function = "MU"
    translation = {"ON":True,"OFF":False}


class DenonWithFeatures(type):
    features = dict(
        maxvol = DenonFeature_Maxvol,
        volume = DenonFeature_Volume,
        muted = DenonFeature_Muted,
        is_running = DenonFeature_Power,
    )
    
    def __new__(self,name,bases,dct):
        dct.update({
            k:property(
                lambda self,k=k:self.features[k].get(),
                lambda self,val,k=k:self.features[k].set(val),
            )
            for k,v in self.features.items()
        })

        def init(obj,*args,_init=dct.get("__init__"),**xargs):
            obj.features = {k:v(obj,k) for k,v in self.features.items()}
            if _init: _init(obj,*args,**xargs)
        dct["__init__"] = init
        return super().__new__(self,name,bases,dct)
    
    
