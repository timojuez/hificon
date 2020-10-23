import sys, math
from ..amp import TelnetAmp, make_amp, features


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
    
        
class _Translation:
    translation = {} #{return_string:value} decode return_string to value / encode vice versa

    options = property(lambda self: list(self.translation.values()))
    
    def decodeVal(self, val): return self.translation.get(val,val)
        
    def encodeVal(self, val):
        return {val:key for key,val in self.translation.items()}.get(val,val)


class _PresetValue:
    """ Inherit if feature value shall have a preset value. Set value in inherited class. """
    value = None

    def __init__(self,*args,**xargs):
        super().__init__(*args,**xargs)
        self._val = self.value
    def get(self): return self._val # skip amp.connected check; TODO: move this to features.py.AsyncFeature.get
    def unset(self): self._val = self.value


class _Constant(_PresetValue):
    """ Inerhit if feature value may not change """
    def matches(self,*args,**xargs): return False
    def store(self,*args,**xargs): pass


######### Data Types

class SelectFeature(_Translation, DenonFeature, features.SelectFeature): pass

class FloatFeature(DenonFeature, features.FloatFeature):

    @staticmethod
    def _roundVolume(vol): return .5*round(vol/.5)

    def decodeVal(self, val): return int(val.ljust(3,"0"))/10
        
    def encodeVal(self, val):
        val = self._roundVolume(val)
        return "%02d"%val if val.is_integer() else "%03d"%(val*10)


class IntFeature(DenonFeature, features.IntFeature):
    min = 0
    max = 99
    
    def encodeVal(self, val):
        digits = math.ceil(math.log(self.max+1,10))
        return ("%%0%dd"%digits)%val
    
    def decodeVal(self, val): return int(val)
        

class BoolFeature(_Translation, DenonFeature, features.BoolFeature):
    translation = {"ON":True,"OFF":False}
    

class RelativeInt(IntFeature):
    min = -6
    max = 6
    default_value = 0
    
    def encodeVal(self, val): return super().encodeVal(val+50)
    def decodeVal(self, val): return super().decodeVal(val)-50
    

class RelativeFloat(FloatFeature):
    min = -12
    max = 12
    default_value = 0
    
    def encodeVal(self, val): return super().encodeVal(val+50)
    def decodeVal(self, val): return super().decodeVal(val)-50
    
    
class _LooseNumericFeature:
    """ Value where the amp does not always send a numeric """
    
    def matches(self, data):
        try:
            assert(super().matches(data))
            self.decode(data)
            return True
        except (TypeError, ValueError, AssertionError): return False


class LooseFloatFeature(_LooseNumericFeature, RelativeFloat): pass

class LooseIntFeature(_LooseNumericFeature, IntFeature): pass

class LooseBoolFeature(BoolFeature):
    """ Value where the amp does not always send a boolean """

    def matches(self,data):
        return super().matches(data) and isinstance(self.decode(data), bool)

    def on_change(self, old, new):
        if new == True: self.amp.send(self.call) # make amp send the nonbool value TODO: only once


######### Features implementation (see Denon CLI protocol)

class Volume(FloatFeature):
    function = "MV"
    def set(self, value, **xargs): super().set(min(max(self.min,value),self.max), **xargs)
    def matches(self, data): return data.startswith(self.function) and "MVMAX" not in data
    
class Maxvol(FloatFeature): #undocumented
    name = "Max. Vol."
    function="MVMAX "
    call="MV?"
    default_value = 98
    def set(self, val, **xargs): raise RuntimeError("Cannot set MVMAX! Set '%s' instead."%VolumeLimit.name)
    def on_change(self, old, new): self.amp.features["volume"].max = new

class VolumeLimit(_PresetValue, SelectFeature): #undocumented
    name = "Volume Limit"
    function="SSVCTZMALIM "
    value = "(select)"
    translation = {"OFF":"Off", "060":"60", "070":"70", "080":"80"}
    def unset(self): self._val = "(select)"
    def on_change(self, old, new): self.amp.features["maxvol"].async_poll(force=True)
    #def async_poll(self,*args,**xargs): self.amp.features["maxvol"].async_poll(,*args,**xargs)
    #def poll(self,*args,**xargs): self.amp.features["maxvol"].poll(,*args,**xargs)

class _SpeakerConfig(SelectFeature):
    call = "SSSPC ?"
    translation = {"SMA":"Small","LAR":"Large","NON":"None"}

class FrontSpeakerConfig(_SpeakerConfig): #undocumented
    name = "Front Speaker Config."
    function = "SSSPCFRO "
    
class SurroundSpeakerConfig(_SpeakerConfig): #undocumented
    name = "Surround Speaker Config."
    function = "SSSPCSUA "
    
class CenterSpeakerConfig(_SpeakerConfig): #undocumented
    name = "Center Speaker Config."
    function = "SSSPCCEN "
    
class SurroundBackSpeakerConfig(_SpeakerConfig): #undocumented
    name = "Surround Back Speaker Config."
    function = "SSSPCSBK "
    
class FrontHeightSpeakerConfig(_SpeakerConfig): #undocumented
    name = "Front Height Speaker Config."
    function = "SSSPCFRH "
    
class TopFrontSpeakerConfig(_SpeakerConfig): #undocumented
    name = "Top Front Speaker Config."
    function = "SSSPCTFR "
    
class TopMiddleSpeakerConfig(_SpeakerConfig): #undocumented
    name = "Top Middle Speaker Config."
    function = "SSSPCTPM "
    
class FrontAtmosSpeakerConfig(_SpeakerConfig): #undocumented
    name = "Front Atmos Speaker Config."
    function = "SSSPCFRD "
    
class SurroundAtmosSpeakerConfig(_SpeakerConfig): #undocumented
    name = "Surround Atmos Speaker Config."
    function = "SSSPCSUD "
    
class SubwooferSpeakerConfig(_SpeakerConfig): #undocumented
    name = "Subwoofer Speaker Config."
    function = "SSSPCSWF "
    translation = {"YES":"Yes","NO":"No"}
    
class Power(BoolFeature):
    function = "PW"
    translation = {"ON":True,"STANDBY":False}
    
    def on_change(self, old, new):
        try: func = {True:self.amp.on_poweron, False:self.amp.on_poweroff}[new]
        except KeyError: return
        else: return func()
    
class Muted(BoolFeature): function = "MU"

class Source(SelectFeature):
    function = "SI"
    # TODO: options

class Name(SelectFeature): #undocumented
    function = "NSFRN "
    options = property(lambda self:[self.get()])
    def set(self, val, **xargs): raise RuntimeError("Cannot set value!")

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
    translation = {"DVD":"DVD", "BD": "Blu-Ray", "TV":"TV", "SAT/CBL": "CBL/SAT", "DVR": "DVR", "GAME": "Game", "GAME2": "Game2", "V.AUX":"V.Aux", "DOCK": "Dock", "SOURCE":"cancel", "OFF":"Off"}

class MainZoneSleep(IntFeature):
    min = 0 # 1..120, 0 will send "OFF"
    max = 120
    name = "Main Zone Sleep (minutes)"
    function = "SLP"
    def encodeVal(self, val): return "OFF" if val==0 else super().encodeVal(val)
    def decodeVal(self, val): return 0 if val=="OFF" else super().decodeVal(val)
    

class Surround(SelectFeature):
    name = "Surround Mode"
    function = "MS"
    translation = {"MOVIE":"Movie", "MUSIC":"Music", "GAME":"Game", "DIRECT": "Direct", "PURE DIRECT":"Pure Direct", "STEREO":"Stereo", "STANDARD": "Standard", "DOLBY DIGITAL":"Dolby Digital", "DTS SURROUND":"DTS Surround", "MCH STEREO":"Multi ch. Stereo", "ROCK ARENA":"Rock Arena", "JAZZ CLUB":"Jazz Club", "MONO MOVIE":"Mono Movie", "MATRIX":"Matrix", "VIDEO GAME":"Video Game", "VIRTUAL":"Virtual",
        "VIRTUAL:X":"DTS Virtual:X","NEURAL:X":"DTS Neural:X","DOLBY SURROUND":"Dolby Surround","M CH IN+DS":"Multi Channel In + Dolby S.", "M CH IN+NEURAL:X": "Multi Channel In + DTS Neural:X", "M CH IN+VIRTUAL:X":"Multi Channel In + DTS Virtual:X", "MULTI CH IN":"Multi Channel In", #undocumented
    }
    def matches(self, data): return super().matches(data) and not data.startswith("MSQUICK")
    
    
class QuickSelect(SelectFeature):
    name = "Quick Select (load)"
    function="MSQUICK"
    call="MSQUICK ?"
    translation = {"0":"(None)", **{str(n+1):str(n+1) for n in range(5)}}

class QuickSelectStore(_Constant, QuickSelect):
    name = "Quick Select (save)"
    value = "(select)"
    def encode(self, value): return "QUICK%s MEMORY"%value

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
    
class _Resolution(SelectFeature):
    translation = {"48P":"480p/576p", "10I":"1080i", "72P":"720p", "10P":"1080p", "10P24":"1080p:24Hz", "AUTO":"Auto"}

class Resolution(_Resolution):
    function = "VSSC"
    call = "VSSC ?"
    def matches(self, data): return super().matches(data) and not data.startswith("VSSCH")
    
class HDMIResolution(_Resolution):
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
    name = "Front Height"
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
    translation = {"NGT":"Midnight", "EVE":"Evening", "DAY":"Day", "OFF":"Off"}
    
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
    
class Bass(RelativeInt): function = "PSBAS "
    
class Treble(RelativeInt): function = "PSTRE "
    
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
        quick_select_store = QuickSelectStore,
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
        front_speaker_config = FrontSpeakerConfig,
        surround_speaker_config = SurroundSpeakerConfig,
        center_speaker_config = CenterSpeakerConfig,
        surround_back_speaker_config = SurroundBackSpeakerConfig,
        front_height_speaker_config = FrontHeightSpeakerConfig,
        top_front_speaker_config = TopFrontSpeakerConfig,
        top_middle_speaker_config = TopMiddleSpeakerConfig,
        front_atmos_speaker_config = FrontAtmosSpeakerConfig,
        surround_atmos_speaker_config = SurroundAtmosSpeakerConfig,
        subwoofer_speaker_config = SubwooferSpeakerConfig,
        volume_limit = VolumeLimit,
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
    
    def send(self, cmd): super().send(cmd.upper())


Amp = make_amp(features, DenonAmp)

