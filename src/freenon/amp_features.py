class AbstractFeature(object):
    function = "" #AVR function command
    function_call = property(lambda self: "%s?"%self.function)
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

    def __init__(self, amp, name):
        self.amp = amp

    def get(self):
        if not self.amp.connected: 
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
        
    def unset(self): self.__dict__.pop("_val",None)
        
    def poll(self):
        try: cmd = self.amp(self.function_call, ret=self.matches)
        except RuntimeError: return self.store(self.default_value)
        else: return self.consume(cmd)
        
    def store(self, value):
        old = getattr(self,'_val',None)
        self._val = value
        if self._val != old: self.on_change(old, self._val)
        return old, self._val


def make_amp_mixin(**features):
    def __init__(self,*args,**xargs):
        self.features = {k:v(self,k) for k,v in features.items()}
        super(cls, self).__init__(*args,**xargs)
    
    def on_connect(self):
        for f in self.features.values(): f.unset()
        super(cls, self).on_connect()
        
    dict_ = dict(__init__=__init__, on_connect=on_connect)
    dict_.update({
        k:property(
            lambda self,k=k:self.features[k].get(),
            lambda self,val,k=k:self.features[k].set(val),
        )
        for k,v in features.items()
    })
    cls = type("AmpFeatures", (object,), dict_)
    return cls


class DenonFeature(Feature):

    def send(self, value=None):
        if value is None: value = self._val
        cmd = "%s%s"%(self.function, self.encodeVal(value))
        self.amp(cmd)
    
    def consume(self, cmd):
        """
        Update property according to @cmd
        """
        if not self.matches(cmd):
            raise ValueError("Cannot handle `%s`."%cmd)
        param = cmd[len(self.function):]
        return self.store(self.decodeVal(param))
        
    def matches(self, cmd):
        """ return True if cmd shall be consumed with this class """
        # TODO: maybe switch to asynchronous and remove this function
        return cmd.startswith(self.function) and " " not in cmd.replace(self.function,"",1)
    
        
class NominalFeature(DenonFeature):
    translation = {} #return_string to value

    def decodeVal(self, val):
        return self.translation.get(val,val)
        
    def encodeVal(self, val):
        return {val:key for key,val in self.translation.items()}.get(val,val)
        

class FloatFeature(DenonFeature):

    @staticmethod
    def _roundVolume(vol):
        return .5*round(vol/.5)

    def decodeVal(self, val):
        return int(val.ljust(3,"0"))/10
        
    def encodeVal(self, val):
        return "%03d"%(self._roundVolume(val)*10)
        

######### Features implementation (see Denon CLI protocol)

class Denon_Volume(FloatFeature):
    function = "MV"
    # TODO: value may be relative?

    
class Denon_Maxvol(FloatFeature):
    function="MVMAX "
    function_call="MV?"
    default_value = 98

    def set(self, val):
        raise RuntimeError("Cannot set MVMAX!")
        
    def send(self): pass
        

class Denon_Power(NominalFeature):
    function = "PW"
    translation = {"ON":True,"STANDBY":False}
    
    def on_change(self, old, new):
        return {True:self.amp.on_avr_poweron, False:self.amp.on_avr_poweroff}[new]()
    
    
class Denon_Muted(NominalFeature):
    function = "MU"
    translation = {"ON":True,"OFF":False}


class Denon_Source(NominalFeature):
    function = "SI"
    
    
class Denon_SubwooferVolume(FloatFeature):
    function = "CVSW "
    function_call = "CV?"
    

DenonMixin = make_amp_mixin(
        maxvol = Denon_Maxvol,
        volume = Denon_Volume,
        muted = Denon_Muted,
        is_running = Denon_Power,
        source = Denon_Source,
        sub_volume = Denon_SubwooferVolume,
)

