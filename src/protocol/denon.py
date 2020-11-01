import sys, math
from decimal import Decimal, InvalidOperation
from ..amp import TelnetAmp, make_amp, features
from ..config import config


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


######### Data Types

class SelectFeature(_Translation, DenonFeature, features.SelectFeature): pass

class DecimalFeature(DenonFeature, features.DecimalFeature):

    @staticmethod
    def _roundVolume(vol): return Decimal('.5')*round(vol/Decimal('.5'))

    def decodeVal(self, val): return Decimal(val.ljust(3,"0"))/10
        
    def encodeVal(self, val):
        val = self._roundVolume(val)
        return "%02d"%val if val%1 == 0 else "%03d"%(val*10)


class IntFeature(DenonFeature, features.IntFeature):
    min = 0
    max = 99
    
    def encodeVal(self, val):
        longestValue = max(abs(self.max),abs(self.min))
        digits = math.ceil(math.log(longestValue+1,10))
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
    

class RelativeDecimal(DecimalFeature):
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
        except (TypeError, ValueError, AssertionError, InvalidOperation): return False


class LooseDecimalFeature(_LooseNumericFeature, RelativeDecimal): pass

class LooseIntFeature(_LooseNumericFeature, IntFeature): pass

class LooseBoolFeature(BoolFeature):
    """ Value where the amp does not always send a boolean """

    def matches(self,data):
        return super().matches(data) and isinstance(self.decode(data), bool)

    def on_change(self, old, new):
        if new == True: self.amp.send(self.call) # make amp send the nonbool value TODO: only once


######### Features implementation (see Denon CLI protocol)

class Volume(DecimalFeature):
    category = "Volume"
    function = "MV"
    def set(self, value, **xargs): super().set(min(max(self.min,value),self.max), **xargs)
    def matches(self, data): return data.startswith(self.function) and "MVMAX" not in data
    
class Maxvol(DecimalFeature): #undocumented
    name = "Max. Vol."
    category = "Volume"
    function="MVMAX "
    call="MV?"
    default_value = 98
    def set(self, val, **xargs): raise RuntimeError("Cannot set MVMAX! Set '%s' instead."%VolumeLimit.name)
    def on_change(self, old, new): self.amp.features["volume"].max = new

class VolumeLimit(features.PresetValue, SelectFeature): #undocumented
    name = "Volume Limit"
    category = "Volume"
    function="SSVCTZMALIM "
    value = "(select)"
    translation = {"OFF":"Off", "060":"60", "070":"70", "080":"80"}
    def unset(self): self._val = "(select)"
    def on_change(self, old, new): self.amp.features["maxvol"].async_poll(force=True)
    #def async_poll(self,*args,**xargs): self.amp.features["maxvol"].async_poll(,*args,**xargs)
    #def poll(self,*args,**xargs): self.amp.features["maxvol"].poll(,*args,**xargs)

class _SpeakerConfig(SelectFeature):
    category = "Speakers"
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
    category = "Misc"
    function = "PW"
    translation = {"ON":True,"STANDBY":False}
    
    def on_change(self, old, new):
        try: func = {True:self.amp.on_poweron, False:self.amp.on_poweroff}[new]
        except KeyError: return
        else: return func()
    
class Muted(BoolFeature):
    category = "Volume"
    function = "MU"

class Source(SelectFeature):
    category = "Input"
    function = "SI"
    translation = config.getdict("Amp","sources")
    
class SourceOptions(SelectFeature): #undocumented
    name = "Source Options"
    category = "Input"
    function = "SSFUN"
    call = "SSFUN ?"
    translation = {}
    _ready = False

    def isset(self): return self._ready
    def decodeVal(self, val):
        if val.strip() == "END":
            self._ready = True
            return
        code, name = val.split(" ",1)
        self.translation[code] = name
    def unset(self): self._ready = False
    def get(self): return "(select)"
    def encode(self, value):
        return "%s%s"%("SI", self.encodeVal(value))


class Name(SelectFeature): #undocumented
    function = "NSFRN "
    def set(self, val, **xargs): raise RuntimeError("Cannot set value!")

class _ChannelVolume(RelativeDecimal):
    category = "Volume"
    call = "CV?"

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
    category = "Input"
    translation = {"AUTO":"Auto", "HDMI":"HDMI", "DIGITAL":"Digital", "ANALOG": "Analog"}
    function = "SD"

class DigitalInput(SelectFeature):
    name = "Digital Input"
    category = "Input"
    function = "DC"
    translation = {"AUTO":"Auto", "PCM": "PCM", "DTS":"DTS"}
    
class VideoSelect(SelectFeature):
    name =" Video Select Mode"
    category = "Video"
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
    category = "Misc"
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

class QuickSelectStore(features.Constant, QuickSelect):
    name = "Quick Select (save)"
    value = "(select)"
    def encode(self, value): return "QUICK%s MEMORY"%value

class HDMIMonitor(SelectFeature):
    name =" HDMI Monitor auto detection"
    category = "Video"
    function = "VSMONI"
    call = "VSMONI ?"
    translation = {"MONI1":"OUT-1", "MONI2":"OUT-2"}
    
class Asp(SelectFeature):
    name = "ASP mode"
    function = "VSASP"
    call = "VSASP ?"
    translation = {"NRM":"Normal", "FUL":"Full"}
    
class _Resolution(SelectFeature):
    category = "Video"
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
    category = "Video"
    function = "VSAUDIO "
    translation = {"AMP":"to Amp", "TV": "to TV"}
    
class VideoProcessing(SelectFeature):
    name = "Video Processing Mode"
    category = "Video"
    function = "VSVPM"
    call = "VSVPM ?"
    translation = {"AUTO":"Auto", "GAME":"Game", "MOVI": "Movie"}
    
class ToneCtrl(BoolFeature):
    name = "Tone Control"
    category = "Misc"
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
    category = "Audyssey"
    function = "PSMULTEQ:"
    call = "PSMULTEQ: ?"
    translation = {"AUDYSSEY":"Audyssey", "BYP.LR":"L/R Bypass", "FLAT":"Flat", "MANUAL":"Manual", "OFF":"Off"}
    
class DynEq(BoolFeature):
    name = "Dynamic Eq"
    category = "Audyssey"
    function = "PSDYNEQ "
    
class RefLevel(SelectFeature):
    name = "Reference Level"
    category = "Audyssey"
    function = "PSREFLEV "
    translation = {"0":"0dB","5":"5dB","10":"10dB","15":"15dB"}
    
class DynVol(SelectFeature):
    name = "Dynamic Volume"
    category = "Audyssey"
    function = "PSDYNVOL "
    translation = {"NGT":"Midnight", "EVE":"Evening", "DAY":"Day", "OFF":"Off"}
    
class AudysseyDsx(SelectFeature):
    name = "Audyssey DSX"
    category = "Audyssey"
    function = "PSDSX "
    translation = {"ONH":"On (Height)", "ONW":"On (Wide)","OFF":"Off"}
    
class StageWidth(IntFeature):
    function = "PSSTW "
    name = "Stage Width"

class StageHeight(IntFeature):
    function = "PSSTH "
    name = "Stage Height"
    
class Bass(RelativeInt):
    category = "Misc"
    function = "PSBAS "
    
class Treble(RelativeInt):
    category = "Misc"
    function = "PSTRE "
    
class DRC(SelectFeature):
    function = "PSDRC "
    translation = {"AUTO":"Auto", "LOW":"Low", "MID":"Medium", "HI":"High", "OFF":"Off"}

class DynCompression(SelectFeature):
    function = "PSDCO "
    name = "Dynamic Compression"
    translation = {"LOW":"Low", "MID":"Medium", "HI":"High", "OFF":"Off"}

class LFE(IntFeature):
    category = "Audio"
    function = "PSLFE "
    min=-10
    max=0
    def decodeVal(self, val): return super().decodeVal(val)*-1
    def encodeVal(self, val): return super().encodeVal(val*-1)

class Effect(IntFeature):
    name = "Effect Level"
    function = "PSEFF "
    
class Delay(IntFeature):
    category = "Audio"
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
    
class Subwoofer(BoolFeature):
    category = "Bass"
    function = "PSSWR "

class _SubwooferAdjustment: #undocumented
    category = "Bass"
    #category = "Audio"
    function = "PSSWL "
    name = "Subwoofer Adjustment"

class SubwooferAdjustmentSwitch(_SubwooferAdjustment, LooseBoolFeature): pass

class SubwooferAdjustment(_SubwooferAdjustment,LooseDecimalFeature): pass

class _DialogLevel: #undocumented
    category = "Audio"
    function = "PSDIL "
    name = "Dialog Level"

class DialogLevelSwitch(_DialogLevel, LooseBoolFeature): pass

class DialogLevel(_DialogLevel, LooseDecimalFeature): pass

class RoomSize(SelectFeature):
    name = "Room Size"
    function = "PSRSZ "
    translation = {e:e for e in ["S","MS","M","ML","L"]}
    
class AudioDelay(IntFeature):
    name = "Audio Delay"
    category = "Audio"
    max = 999
    function  ="PSDELAY "

class Restorer(SelectFeature):
    name = "Audio Restorer"
    category = "Audio"
    function = "PSRSTR "
    translation = {"OFF":"Off", "MODE1":"Mode 1", "MODE2":"Mode 2", "MODE3":"Mode 3"}
    
class FrontSpeaker(SelectFeature):
    name = "Front Speaker"
    function = "PSFRONT"
    translation = {" SPA":"A"," SPB":"B"," A+B":"A+B"}
    
class Crossover(SelectFeature): #undocumented
    name = "Crossover Speaker Select"
    category = "Speakers"
    function = "SSCFR "
    translation = {"ALL":"All","IDV":"Individual"}
    def matches(self, data): return super().matches(data) and "END" not in data

class _Crossover(SelectFeature): #undocumented
    category = "Speakers"
    call = "SSCFR ?"
    translation = {x:"%d Hz"%int(x)
        for x in ["040","060","080","090","100","110","120","150","200","250"]}

class CrossoverAll(_Crossover): #undocumented
    name = "Crossover (all)"
    function = "SSCFRALL "
    
class CrossoverFront(_Crossover): #undocumented
    name = "Crossover (front)"
    function = "SSCFRFRO "
    
class CrossoverSurround(_Crossover): #undocumented
    name = "Crossover (surround)"
    function = "SSCFRSUA "

class CrossoverCenter(_Crossover): #undocumented
    name = "Crossover (center)"
    function = "SSCFRCEN "

class CrossoverSurroundBack(_Crossover): #undocumented
    name = "Crossover (surround back)"
    function = "SSCFRSBK "

class CrossoverFrontHeight(_Crossover): #undocumented
    name = "Crossover (front height)"
    function = "SSCFRFRH "

class CrossoverTopFront(_Crossover): #undocumented
    name = "Crossover (top front)"
    function = "SSCFRTFR "

class CrossoverTopMiddle(_Crossover): #undocumented
    name = "Crossover (top middle)"
    function = "SSCFRTPM "

class CrossoverFrontAtmos(_Crossover): #undocumented
    name = "Crossover (front atmos)"
    function = "SSCFRFRD "

class CrossoverSurroundAtmos(_Crossover): #undocumented
    name = "Crossover (surround atmos)"
    function = "SSCFRSUD "

class SubwooferMode(SelectFeature): #undocumented
    name = "Subwoofer Mode"
    category = "Bass"
    function = "SSSWM "
    translation = {"L+M":"LFE + Main", "LFE":"LFE"}
    
class LfeLowpass(SelectFeature): #undocumented
    name = "LFE Lowpass Freq."
    category = "Bass"
    function = "SSLFL "
    translation = {x:"%d Hz"%int(x) 
        for x in ["080","090","100","110","120","150","200","250"]}

class Display(SelectFeature):
    function = "DIM "
    translation = {"BRI":"Bright","DIM":"Dim","DAR":"Dark","OFF":"Off"}


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
        crossover = Crossover,
        crossover_all = CrossoverAll,
        crossover_front = CrossoverFront,
        crossover_surround = CrossoverSurround,
        crossover_center = CrossoverCenter,
        crossover_surround_back = CrossoverSurroundBack,
        crossover_front_height = CrossoverFrontHeight,
        crossover_top_front = CrossoverTopFront,
        crossover_top_middle = CrossoverTopMiddle,
        crossover_front_atmos = CrossoverFrontAtmos,
        crossover_surround_atmos = CrossoverSurroundAtmos,
        subwoofer_mode = SubwooferMode,
        lfe_lowpass = LfeLowpass,
        display = Display,
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

