import sys
from ..amp import Feature, make_amp, make_basic_amp


class DenonFeature(Feature):
    function = "" #Amp function command
    call = property(lambda self: "%s?"%self.function)

    def send(self, value):
        cmd = "%s%s"%(self.function, self.encodeVal(value))
        self.amp(cmd) # TODO: add matches= for synchronous call?
    
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

class Volume(FloatFeature):
    function = "MV"
    # TODO: value may be relative?
    def set(self, value):
        super().set(min(max(0,value),self.amp.maxvol))

    
class Maxvol(FloatFeature):
    function="MVMAX "
    call="MV?"
    default_value = 98

    def set(self, val):
        raise RuntimeError("Cannot set MVMAX!")
        
    def send(self): pass
        

class Power(NominalFeature):
    function = "PW"
    translation = {"ON":True,"STANDBY":False}
    
    def on_change(self, old, new):
        return {True:self.amp.on_poweron, False:self.amp.on_poweroff}[new]()
    
    
class Muted(NominalFeature):
    function = "MU"
    translation = {"ON":True,"OFF":False}


class Source(NominalFeature):
    function = "SI"
    
    
class SubwooferVolume(FloatFeature):
    name = "Subwoofer Volume"
    function = "CVSW "
    call = "CV?"
    

features = dict(
        maxvol = Maxvol,
        volume = Volume,
        muted = Muted,
        power = Power,
        source = Source,
        sub_volume = SubwooferVolume,
)


class Abstract_denon(object):
    protocol = "Denon"
        
    def __call__(self, cmd, matches=None):
        """ 
        Send command to amp
        @cmd str: function[?|param]
        @matches callable: return received line where matches(line) is True
        """
        cmd = cmd.upper()
        if "?" in cmd and not matches:
            function = cmd.replace("?","")
            return "%s%s"%(function,type(function,(NominalFeature,),dict(function=function))(self).get())
        return super().__call__(cmd,matches)
        
    def _send(self, cmd):
        super()._send(cmd.upper())
        
        
class Amp(Abstract_denon, make_amp(**features)): pass
class BasicAmp(Abstract_denon, make_basic_amp(**features)): pass

