import sys, math, time
from ..amp import TelnetAmp, make_amp
from .. import amp_features


class DenonFeature:
    """ Handles Denon format "@function@value" """
    
    function = None #str, Amp function command
    call = property(lambda self: "%s?"%self.function)

    def encode(self, value):
        return "%s%s"%(self.function, self.encodeVal(value))
    
    def decode(self, cmd):
        param = cmd[len(self.function):]
        return self.decodeVal(param)
        
    def matches(self, cmd):
        return cmd.startswith(self.function) #and " " not in cmd.replace(self.function,"",1)
    
        
######### Data Types

class SelectFeature(DenonFeature, amp_features.SelectFeature):
    translation = {} #return_string to value
    
    options = property(lambda self: list(self.translation.values()))

    def decodeVal(self, val):
        r = self.translation[val] = self.translation.get(val,val)
        return r
        
    def encodeVal(self, val):
        return {val:key for key,val in self.translation.items()}.get(val,val)
        

class FloatFeature(DenonFeature, amp_features.FloatFeature):

    @staticmethod
    def _roundVolume(vol):
        return .5*round(vol/.5)

    def decodeVal(self, val):
        return int(val.ljust(3,"0"))/10
        
    def encodeVal(self, val):
        val = self._roundVolume(val)
        return "%02d"%val if val.is_integer() else "%03d"%(val*10)


class IntFeature(DenonFeature, amp_features.IntFeature):
    min = 0
    max = 99
    
    def encodeVal(self, val):
        digits = math.ceil(math.log(self.max+1,10))
        return ("%%0%dd"%digits)%val
    
    def decodeVal(self, val): 
        try: return int(val)
        except ValueError: return False
        

class BoolFeature(SelectFeature, amp_features.BoolFeature):
    translation = {"ON":True,"OFF":False}
    

class RelativeFloat(FloatFeature):
    min = -12
    max = 12
    default_value = 0
    
    def encodeVal(self, val): return super().encodeVal(val+50)
    def decodeVal(self, val): return super().decodeVal(val)-50
    
    
class LooseFloatFeature(RelativeFloat, BoolFeature):
    """ Value where the amp does not always send a float """
    
    def matches(self, data):
        try:
            assert(super().matches(data))
            self.decode(data)
            return True
        except (TypeError, ValueError, AssertionError): return False


class LooseBoolFeature(BoolFeature):
    """ Value where the amp does not always send a boolean """

    def matches(self,data):
        return super().matches(data) and isinstance(self.decode(data), bool)

    def on_change(self, old, new):
        if new == True: self.amp.send(self.call) # make amp send the nonbool value TODO: only once


######### Features implementation (see Denon CLI protocol)

class Volume(FloatFeature):
    function = "MV"
    def set(self, value): super().set(min(max(0,value),self.amp.maxvol))
    def matches(self, data): return data.startswith(self.function) and "MVMAX" not in data
    
class Maxvol(FloatFeature): #undocumented
    function="MVMAX "
    call="MV?"
    default_value = 98
    def set(self, val): raise RuntimeError("Cannot set MVMAX!")
    def on_change(self, old, new): self.amp.features["volume"].max = new

class Power(SelectFeature):
    function = "PW"
    translation = {"ON":True,"STANDBY":False}
    
    def on_change(self, old, new):
        try: func = {True:self.amp.on_poweron, False:self.amp.on_poweroff}[new]
        except KeyError: return
        else: return func()
    
class Muted(SelectFeature):
    function = "MU"
    translation = {"ON":True,"OFF":False}

class Source(SelectFeature):
    function = "SI"

class Name(SelectFeature): #undocumented
    function = "NSFRN "
    def set(self, val): raise RuntimeError("Cannot set value!")

class _ChannelVolume(RelativeFloat): call = "CV?"

class FrontLeftVolume(_ChannelVolume):
    name = "Front L Volume"
    function = "CVFL "

class FrontRightVolume(_ChannelVolume):
    name = "Front R Volume"
    function = "CVFR "

class CenterVolume(_ChannelVolume):
    name = "Center Volume"
    function = "CVC "

class SubwooferVolume(_ChannelVolume):
    name = "Subwoofer Volume"
    function = "CVSW "
    
class SurroundLeftVolume(_ChannelVolume):
    name = "Surround L Volume"
    function = "CVSL "
    
class SurroundRightVolume(_ChannelVolume):
    name = "Surround R Volume"
    function = "CVSR "
    
class SurroundBackLeftVolume(_ChannelVolume):
    name = "Surround Back L Volume"
    function = "CVSBL "
    
class SurroundBackRightVolume(_ChannelVolume):
    name = "Surround Back R Volume"
    function = "CVSBR "
    
class SurroundBackVolume(_ChannelVolume):
    name = "Surround Back Volume"
    function = "CVSB "

class FrontHeightLeftVolume(_ChannelVolume):
    name = "Front Height L Volume"
    function = "CVFHL "

class FrontHeightRightVolume(_ChannelVolume):
    name = "Front Height R Volume"
    function = "CVFHR "

class FrontWideLeftVolume(_ChannelVolume):
    name = "Front Wide L Volume"
    function = "CVFWL "

class FrontWideRightVolume(_ChannelVolume):
    name = "Front Wide R Volume"
    function = "CVFWR "

class MainZone(BoolFeature):
    name = "Main Zone"
    function = "ZM"
    
class RecSelect(SelectFeature):
    name = "Rec Select"
    function = "SR"

class InputMode(SelectFeature):
    name = "Input Mode"
    translation = {"AUTO":"Auto", "HDMI":"HDMI", "DIGITAL":"Digital", "ANALOG": "Analog"}
    function = "SD"

class DigitalInput(SelectFeature):
    name = "Digital Input"
    function = "DC"
    translation = {"AUTO":"Auto", "PCM": "PCM", "DTS":"DTS"}
    
class VideoSelect(SelectFeature):
    name =" Video Select Mode"
    function = "SV"
    translation = {"DVD":"DVD", "BD": "Blu-Ray", "TV":"TV", "SAT/CBL": "CBL/SAT", "DVR": "DVR", "GAME": "Game", "GAME2": "Game2", "V.AUX":"V.Aux", "DOCK": "Dock", "SOURCE":"cancel"}

class MainZoneSleep(IntFeature):
    min = 1
    max = 120
    name = "Main Zone Sleep (minutes)"
    function = "SLP"
    # TODO: OFF

class Surround(SelectFeature):
    name = "Surround Mode"
    function = "MS"
    translation = {"MOVIE":"Movie", "MUSIC":"Music", "GAME":"Game", "DIRECT": "Direct", "PURE DIRECT":"Pure Direct", "STEREO":"Stereo", "STANDARD": "Standard", "DOLBY DIGITAL":"Dolby Digital", "DTS SURROUND":"DTS Surround", "MCH STEREO":"Multi ch. Stereo", "ROCK ARENA":"Rock Arena", "JAZZ CLUB":"Jazz Club", "MONO MOVIE":"Mono Movie", "MATRIX":"Matrix", "VIDEO GAME":"Video Game", "VIRTUAL":"Virtual"}
    
class QuickSelect(SelectFeature):
    name = "Quick Select"
    function="MSQUICK"
    call="MSQUICK ?"
    translation = {str(n+1):str(n+1) for n in range(5)}

"""
class QuickSelectSave(SelectFeature):
    name = "Quick Select (save)"
    def encode(self, value): return "QUICK%s MEMORY"%value
    def get(self): raise AttributeError("Cannot read value")
""" # TODO

class HDMIMonitor(SelectFeature):
    name =" HDMI Monitor auto detection"
    function = "VSMONI"
    call = "VSMONI ?"
    translation = {"MONI1":"OUT-1", "MONI2":"OUT-2"}
    
class Asp(SelectFeature):
    name = "ASP mode"
    function = "VSASP"
    call = "VSASP ?"
    translation = {"NRM":"Normal", "FUL":"Full"}
    
class Resolution(SelectFeature):
    function = "VSSC"
    call = "VSSC ?"
    translation = {"48P":"480p/576p", "10I":"1080i", "72P":"720p", "10P":"1080p", "10P24":"1080p:24Hz", "AUTO":"Auto"}
    
class HDMIResolution(Resolution):
    name = "HDMI Resolution"
    function = "VSSCH"
    call = "VSSCH ?"

class HDMIAudioOut(SelectFeature):
    name = "HDMI Audio Output"
    function = "VSAUDIO "
    translation = {"AMP":"to Amp", "TV": "to TV"}
    
class VideoProcessing(SelectFeature):
    name = "Video Processing Mode"
    function = "VSVPM"
    call = "VSVPM ?"
    translation = {"AUTO":"Auto", "GAME":"Game", "MOVI": "Movie"}
    
class ToneCtrl(BoolFeature):
    name = "Tone Control"
    function = "PSTONE CTRL "
    
class SurroundBackMode(SelectFeature):
    name = "Surround Back SP Mode"
    function = "PSSB:"
    call = "PSSB: ?"
    translation = {"MTRX ON": "Matrix", "PL2x CINEMA":"Cinema", "PL2x MUSIC": "Music", "ON":"On", "OFF":"Off"}
    
class CinemaEq(BoolFeature):
    name = "Cinema Eq."
    function = "PSCINEMA EQ."
    call = "PSCINEMA EQ. ?"

class Mode(SelectFeature):
    function = "PSMODE:"
    call = "PSMODE: ?"
    translation = {"MUSIC":"Music","CINEMA":"Cinema","GAME":"Game","PRO LOGIC":"Pro Logic"}
    
class FrontHeight(BoolFeature):
    function = "PSFH:"
    call = "PSFH: ?"

class PL2HG(SelectFeature):
    name = "PL2z Height Gain"
    function = "PSPHG "
    translation = {"LOW":"Low","MID":"Medium","HI":"High"}
    
class SpeakerOutput(SelectFeature):
    name = "Speaker Output"
    function = "PSSP:"
    call = "PSSP: ?"
    translation = {"FH":"F. Height", "FW":"F. Wide", "SB":"S. Back"}
    
class MultiEQ(SelectFeature):
    name = "MultiEQ XT mode"
    function = "PSMULTEQ:"
    call = "PSMULTEQ: ?"
    translation = {"AUDYSSEY":"Audyssey", "BYP.LR":"L/R Bypass", "FLAT":"Flat", "MANUAL":"Manual", "OFF":"Off"}
    
class DynEq(BoolFeature):
    name = "Dynamic Eq"
    function = "PSDYNEQ "
    
class RefLevel(SelectFeature):
    name = "Reference Level"
    function = "PSREFLEV "
    translation = {"0":"0dB","5":"5dB","10":"10dB","15":"15dB"}
    
class DynVol(SelectFeature):
    name = "Dynamic Volume"
    function = "PSDYNVOL "
    translation = {"NGT":"Midnight", "EVE":"Evening", "DAY":"Day"}
    
class AudysseyDsx(SelectFeature):
    name = "Audyssey DSX"
    function = "PSDSX "
    translation = {"ONH":"On (Height)", "ONW":"On (Wide)","OFF":"Off"}
    
class StageWidth(IntFeature):
    function = "PSSTW "
    name = "Stage Width"

class StageHeight(IntFeature):
    function = "PSSTH "
    name = "Stage Height"
    
class Bass(IntFeature): function = "PSBAS "
    
class Treble(IntFeature): function = "PSTRE "
    
class DRC(SelectFeature):
    function = "PSDRC "
    translation = {"AUTO":"Auto", "LOW":"Low", "MID":"Medium", "HI":"High", "OFF":"Off"}

class DynCompression(SelectFeature):
    function = "PSDCO "
    name = "Dynamic Compression"
    translation = {"LOW":"Low", "MID":"Medium", "HI":"High", "OFF":"Off"}

class LFE(IntFeature): function = "PSLFE "

class Effect(IntFeature):
    name = "Effect Level"
    function = "PSEFF "
    
class Delay(IntFeature):
    max=999
    function = "PSDEL "
    name = "Delay"
    
class AFD(BoolFeature):
    name = "AFDM"
    function = "PSAFD "
    
class Panorama(BoolFeature): function = "PSPAN "

class Dimension(IntFeature): function = "PSDIM "

class CenterWidth(IntFeature):
    name = "Center Width"
    function = "PSCEN "
    
class CenterImage(IntFeature):
    name = "Center Image"
    function = "PSCEI "
    
class Subwoofer(BoolFeature): function = "PSSWR "

class _SubwooferAdjustment: #undocumented
    function = "PSSWL "
    name = "Subwoofer Adjustment"

class SubwooferAdjustmentSwitch(_SubwooferAdjustment, LooseBoolFeature): pass

class SubwooferAdjustment(_SubwooferAdjustment,LooseFloatFeature): pass

class _DialogLevel: #undocumented
    function = "PSDIL "
    name = "Dialog Level"

class DialogLevelSwitch(_DialogLevel, LooseBoolFeature): pass

class DialogLevel(_DialogLevel, LooseFloatFeature): pass

class RoomSize(SelectFeature):
    name = "Room Size"
    function = "PSRSZ "
    translation = {e:e for e in ["S","MS","M","ML","L"]}
    
class AudioDelay(IntFeature):
    name = "Audio Delay"
    max = 999
    function  ="PSDELAY "

class Restorer(SelectFeature):
    name = "Audio Restorer"
    function = "PSRSTR "
    translation = {"OFF":"Off", "MODE1":"Mode 1", "MODE2":"Mode 2", "MODE3":"Mode 3"}
    
class FrontSpeaker(SelectFeature):
    name = "Front Speaker"
    function = "PSFRONT"
    translation = {" SPA":"A"," SPB":"B"," A+B":"A+B"}
    

features = dict(
        maxvol = Maxvol,
        volume = Volume,
        muted = Muted,
        power = Power,
        source = Source,
        denon_name = Name,
        front_left_volume = FrontLeftVolume,
        front_right_volume = FrontRightVolume,
        center_volume = CenterVolume,
        sub_volume = SubwooferVolume,
        surround_left_volume = SurroundLeftVolume,
        surround_right_volume = SurroundRightVolume,
        surround_back_left_volume = SurroundBackLeftVolume,
        surround_back_right_volume = SurroundBackRightVolume,
        surround_back_volume = SurroundBackVolume,
        front_height_left_volume = FrontHeightLeftVolume,
        front_height_right_volume = FrontHeightRightVolume,
        front_wide_left_volume = FrontWideLeftVolume,
        front_wide_right_volume = FrontWideRightVolume,
        main_zone = MainZone,
        rec = RecSelect,
        input_mode = InputMode,
        digital_input = DigitalInput,
        video = VideoSelect,
        sleep = MainZoneSleep,
        surround = Surround,
        quick_select = QuickSelect,
        hdmi_monitor = HDMIMonitor,
        asp = Asp,
        resolution = Resolution,
        hdmi_resolution = HDMIResolution,
        hdmi_audio_out = HDMIAudioOut,
        video_processing = VideoProcessing,
        tone_ctrl = ToneCtrl,
        surround_back_mode = SurroundBackMode,
        cinema_eq = CinemaEq,
        mode = Mode,
        front_height = FrontHeight,
        pl2hg = PL2HG,
        speaker_output = SpeakerOutput,
        multi_eq = MultiEQ,
        dyn_eq = DynEq,
        ref_level = RefLevel,
        dyn_vol = DynVol,
        audyssey_dsx = AudysseyDsx,
        stage_width = StageWidth,
        stage_height = StageHeight,
        bass = Bass,
        treble = Treble,
        drc = DRC,
        dyn_compression = DynCompression,
        lfe = LFE,
        effect = Effect,
        delay = Delay,
        afd = AFD,
        panorama = Panorama,
        dimension = Dimension,
        center_width = CenterWidth,
        center_image = CenterImage,
        subwoofer = Subwoofer,
        room_size = RoomSize,
        audio_delay = AudioDelay,
        restorer = Restorer,
        front_speaker = FrontSpeaker,
        subwoofer_adjustment = SubwooferAdjustment,
        subwoofer_adjustment_switch = SubwooferAdjustmentSwitch,
        dialog_level = DialogLevel,
        dialog_level_switch = DialogLevelSwitch,
        # TODO: implement PV
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
        class _Feature(SelectFeature): 
            function=_function
            matches = lambda self, data: (matches(data) if matches else super().matches(data))
        _Feature.__name__ = _function
        return "%s%s"%(_function, _Feature(self).get())
    
    def send(self, cmd):
        super().send(cmd.upper())
        time.sleep(.01) # Denon workaround
        
        
Amp = make_amp(features, DenonAmp)

