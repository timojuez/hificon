import sys
from ..amp import Feature, TelnetAmp, make_amp


class DenonFeature(Feature):
    function = "" #Amp function command
    call = property(lambda self: "%s?"%self.function)

    def send(self, value):
        cmd = "%s%s"%(self.function, self.encodeVal(value))
        self.amp.send(cmd) # TODO: add matches= for synchronous call?
    
    def parse(self, cmd):
        param = cmd[len(self.function):]
        return self.decodeVal(param)
        
    def matches(self, cmd):
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
    def set(self, val): raise RuntimeError("Cannot set MVMAX!")
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
    

class Name(NominalFeature):
    function = "NSFRN "
    def matches(self, cmd): return cmd.startswith(self.function)
    def set(self, val): raise RuntimeError("Cannot set value!")
    def send(self): pass

    
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
        denon_name = Name,
)


class Abstract_denon(object):
    protocol = "Denon"
    
    def query(self, cmd, matches=None):
        """ 
        Send command to amp
        @cmd str: function[?|param]
        @matches callable: return received line where matches(line) is True
        """
        _function = cmd.upper().replace("?","")
        if "?" not in cmd: return self.send(_function)
        class _Feature(NominalFeature): 
            function=_function
            matches = lambda self, data: matches and matches(data) or super().matches(data)
        _Feature.__name__ = _function
        return "%s%s"%(_function, _Feature(self).get())
    
    def send(self, cmd): super().send(cmd.upper())
        
        
class Amp(Abstract_denon, make_amp(features,TelnetAmp)): pass

