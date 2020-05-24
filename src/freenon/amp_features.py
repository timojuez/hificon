class AbstractFeature(object):
    function = "" #AVR function command
    function_call = property(lambda self: "%s?"%self.function)
    function_ret = property(lambda self: self.function) # TODO: maybe switch to asynchronous and remove this function
    default_value = None #if no response
    
    def on_change(self, old, new): pass


class Feature(AbstractFeature):
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
            self.poll()
            return self._val
        
    def set(self, value):
        if getattr(self, "_val", None) == value: return
        #self._val = value
        self.send(value)

    def isset(self):
        return hasattr(self,'_val')
        
    def poll(self):
        try: cmd = self.denon(self.function_call, ret=self.function_ret)
        except RuntimeError: return self.store(self.default_value)
        else: return self.consume(cmd)
    
    def send(self, value=None):
        if value is None: value = self._val
        cmd = "%s%s"%(self.function, self.encodeVal(value))
        self.denon(cmd)
    
    def consume(self, cmd):
        """
        Update property according to @cmd
        """
        if not self.matches(cmd):
            raise ValueError("Cannot handle `%s`."%cmd)
        param = cmd[len(self.function):]
        return self.store(self.decodeVal(param))
        
    def store(self, value):
        old = getattr(self,'_val',None)
        self._val = value
        if self._val != old: self.on_change(old, self._val)
        return old, self._val
        
    def matches(self, cmd):
        """ return True if cmd shall be consumed with this class """
        if callable(self.function_ret): return self.function_ret(cmd)
        else: return cmd.startswith(self.function_ret)
        
        
class NominalFeature(Feature):
    translation = {} #return_string to value

    def decodeVal(self, val):
        return self.translation.get(val,val)
        
    def encodeVal(self, val):
        return {val:key for key,val in self.translation.items()}.get(val,val)
        

class FloatFeature(Feature):

    def set(self, value):
        super().set(self._roundVolume(value))
        
    @staticmethod
    def _roundVolume(vol):
        return .5*round(vol/.5)

    def decodeVal(self, val):
        return int(val.ljust(3,"0"))/10
        
    def encodeVal(self, val):
        return "%03d"%(val*10)
        

class Feature_Volume(FloatFeature):
    function = "MV"
    function_ret = lambda self,s: s.startswith("MV") and s[2] != "M"
    
    # TODO: value may be relative?

    
class Feature_Maxvol(FloatFeature):
    function="MVMAX "
    function_call="MV?"
    default_value = 98

    def set(self, val):
        raise RuntimeError("Cannot set MVMAX!")
        
    def send(self): pass
        

class Feature_Power(NominalFeature):
    function = "PW"
    translation = {"ON":True,"STANDBY":False}
    
    def on_change(self, old, new):
        return {True:self.denon.on_avr_poweron, False:self.denon.on_avr_poweroff}[new]()
    
    
class Feature_Muted(NominalFeature):
    function = "MU"
    translation = {"ON":True,"OFF":False}


class Feature_Source(NominalFeature):
    function = "SI"
    
    
class Feature_SubwooferLevel(FloatFeature):
    function = "CVSW "
    function_call = "CV?"
    

class DenonWithFeatures(type):
    features = dict(
        maxvol = Feature_Maxvol,
        volume = Feature_Volume,
        muted = Feature_Muted,
        is_running = Feature_Power,
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
    
    
