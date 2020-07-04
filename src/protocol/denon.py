import sys
from ..amp import Feature, TelnetAmp, make_amp


class DenonFeature(Feature):
    function = "" #Amp function command
    call = property(lambda self: "%s?"%self.function)

    def encode(self, value):
        return "%s%s"%(self.function, self.encodeVal(value))
    
    def decode(self, cmd):
        param = cmd[len(self.function):]
        return self.decodeVal(param)
        
    def matches(self, cmd):
        return cmd.startswith(self.function) #and " " not in cmd.replace(self.function,"",1)
    
        
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
        val = self._roundVolume(val)
        return "%02d"%val if val.is_integer() else "%03d"%(val*10)
        

######### Features implementation (see Denon CLI protocol)

class FrontSpeaker(NominalFeature):
    function = "PSFRONT"
    translation = {" SPA":"A"," SPB":"B"," A+B":"A+B"}
    

class Volume(FloatFeature):
    function = "MV"
    # TODO: value may be relative?
    def set(self, value): super().set(min(max(0,value),self.amp.maxvol))
    def matches(self, data): return data.startswith(self.function) and "MVMAX" not in data

    
class Maxvol(FloatFeature):
    function="MVMAX "
    call="MV?"
    default_value = 98
    def set(self, val): raise RuntimeError("Cannot set MVMAX!")
        

class Power(NominalFeature):
    function = "PW"
    translation = {"ON":True,"STANDBY":False}
    
    def on_change(self, old, new):
        try: func = {True:self.amp.on_poweron, False:self.amp.on_poweroff}[new]
        except KeyError: return
        else: return func()
    
    
class Muted(NominalFeature):
    function = "MU"
    translation = {"ON":True,"OFF":False}


class Source(NominalFeature):
    function = "SI"
    

class Name(NominalFeature):
    function = "NSFRN "
    def set(self, val): raise RuntimeError("Cannot set value!")

    
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
        front_speaker = FrontSpeaker,
)


class DenonAmp(TelnetAmp):
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
            matches = lambda self, data: not matches and super().matches(data) or matches(data)
        _Feature.__name__ = _function
        return "%s%s"%(_function, _Feature(self).get())
    
    def send(self, cmd): super().send(cmd.upper())
        
        
Amp = make_amp(features, DenonAmp)

