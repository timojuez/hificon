import sys, math
from decimal import Decimal, InvalidOperation
from ..amp import TelnetAmp, make_amp
from ..config import config
from .. import amp

ZONES = 4

features = []
def addToAmp(cls):
    global features
    features.append(cls)
    return cls


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

class SelectFeature(_Translation, DenonFeature, amp.features.SelectFeature): pass

class DecimalFeature(DenonFeature, amp.features.DecimalFeature):

    @staticmethod
    def _roundVolume(vol): return Decimal('.5')*round(vol/Decimal('.5'))

    def decodeVal(self, val): return Decimal(val.ljust(3,"0"))/10
        
    def encodeVal(self, val):
        val = self._roundVolume(val)
        return "%02d"%val if val%1 == 0 else "%03d"%(val*10)


class IntFeature(DenonFeature, amp.features.IntFeature):
    min = 0
    max = 99
    
    def encodeVal(self, val):
        longestValue = max(abs(self.max),abs(self.min))
        digits = math.ceil(math.log(longestValue+1,10))
        return ("%%0%dd"%digits)%val
    
    def decodeVal(self, val): return int(val)
        

class BoolFeature(_Translation, DenonFeature, amp.features.BoolFeature):
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
        super().on_change(old, new)
        if new == True: self.amp.send(self.call) # make amp send the nonbool value TODO: only once


######### Features implementation (see Denon CLI protocol)

@addToAmp
class Volume(DecimalFeature):
    category = "Volume"
    function = "MV"
    def set(self, value, **xargs): super().set(min(max(self.min,value),self.max), **xargs)
    def matches(self, data): return data.startswith(self.function) and data[len(self.function):].isnumeric()
    
@addToAmp
class Maxvol(DecimalFeature): #undocumented
    name = "Max. Vol."
    category = "Volume"
    function="MVMAX "
    call="MV?"
    default_value = 98
    def set(self, val, **xargs): raise RuntimeError("Cannot set MVMAX! Set '%s' instead."%VolumeLimit.name)

@addToAmp
class Volume_limit(SelectFeature): #undocumented
    category = "Volume"
    function="SSVCTZMALIM "
    call = "SSVCTZMA ?"
    translation = {"OFF":"Off", "060":"60", "070":"70", "080":"80"}
    def on_change(self, old, new):
        super().on_change(old, new)
        self.amp.features["maxvol"].async_poll(force=True)

class _SpeakerConfig(SelectFeature):
    category = "Speakers"
    call = "SSSPC ?"
    translation = {"SMA":"Small","LAR":"Large","NON":"None"}

@addToAmp
class Front_speaker_config(_SpeakerConfig): #undocumented
    function = "SSSPCFRO "
    
@addToAmp
class Surround_speaker_config(_SpeakerConfig): #undocumented
    function = "SSSPCSUA "
    
@addToAmp
class Center_speaker_config(_SpeakerConfig): #undocumented
    function = "SSSPCCEN "
    
@addToAmp
class Surround_back_speaker_config(_SpeakerConfig): #undocumented
    function = "SSSPCSBK "
    
@addToAmp
class Front_height_speaker_config(_SpeakerConfig): #undocumented
    function = "SSSPCFRH "
    
@addToAmp
class Top_front_speaker_config(_SpeakerConfig): #undocumented
    function = "SSSPCTFR "
    
@addToAmp
class Top_middle_speaker_config(_SpeakerConfig): #undocumented
    function = "SSSPCTPM "
    
@addToAmp
class Front_atmos_speaker_config(_SpeakerConfig): #undocumented
    function = "SSSPCFRD "
    
@addToAmp
class Surround_atmos_speaker_config(_SpeakerConfig): #undocumented
    function = "SSSPCSUD "
    
@addToAmp
class Subwoofer_speaker_config(_SpeakerConfig): #undocumented
    function = "SSSPCSWF "
    translation = {"YES":"Yes","NO":"No"}
    
@addToAmp
class Power(BoolFeature):
    category = "Misc"
    function = "PW"
    translation = {"ON":True,"STANDBY":False}
    
    def on_change(self, old, new):
        super().on_change(old, new)
        try: func = {True:self.amp.on_poweron, False:self.amp.on_poweroff}[new]
        except KeyError: return
        else: return func()
    
@addToAmp
class Muted(BoolFeature):
    category = "Volume"
    function = "MU"

@addToAmp
class Source(SelectFeature):
    category = "Input"
    function = "SI"
    translation = {"PHONO":"Phono", "CD":"CD", "TUNER":"Tuner", "DVD":"DVD",
        "BD":"Blu-ray","TV":"TV","SAT/CBL":"CBL/SAT","MPLAY":"Media Player",
        "GAME":"Game","HDRADIO":"HD Radio","NET":"Heos","PANDORA":"Pandora",
        "SIRIUSXM":"Sirius XM","SPOTIFY":"Spotify","LASTFM":"Last FM",
        "FLICKR":"Flickr","IRADIO":"IRadio","SERVER":"Server",
        "FAVORITES":"Favourites","AUX1":"AUX 1","AUX2":"AUX 2","AUX3":"AUX 3",
        "AUX4":"AUX 4","AUX5":"AUX 5","AUX6":"AUX 6","AUX7":"AUX 7","BT":"Bluetooth",
        "USB/IPOD":"USB/Ipod","USB":"USB","IPD":"IPD","IRP":"IRP","FVP":"FVP",
        **config.getdict("Amp","source_names")}
    
class Source_names(SelectFeature): #undocumented
    """
    SSFUN ?
    SSFUNSAT/CBL CBL/SAT
    SSFUNMPLAY Media Player
    SSFUN END    
    """
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
        self.amp.features["source"].translation[code] = name
    def unset(self): self._ready = False
    def get(self): return "(select)"
    def encode(self, value):
        return "%s%s"%("SI", self.encodeVal(value))


@addToAmp
class Denon_name(SelectFeature): #undocumented
    function = "NSFRN "
    def set(self, val, **xargs): raise RuntimeError("Cannot set value!")

class _Channel_volume(RelativeDecimal):
    category = "Volume"
    call = "CV?"

@addToAmp
class Front_left_volume(_Channel_volume): function = "CVFL "

@addToAmp
class Front_right_volume(_Channel_volume): function = "CVFR "

@addToAmp
class Center_volume(_Channel_volume): function = "CVC "

@addToAmp
class Subwoofer_volume(_Channel_volume): function = "CVSW "
    
@addToAmp
class Surround_left_volume(_Channel_volume): function = "CVSL "
    
@addToAmp
class Surround_right_volume(_Channel_volume): function = "CVSR "
    
@addToAmp
class Surround_back_left_volume(_Channel_volume):
    name = "Surround Back L Volume"
    function = "CVSBL "
    
@addToAmp
class Surround_back_right_volume(_Channel_volume):
    name = "Surround Back R Volume"
    function = "CVSBR "
    
@addToAmp
class Surround_back_volume(_Channel_volume): function = "CVSB "

@addToAmp
class Front_height_left_volume(_Channel_volume):
    name = "Front Height L Volume"
    function = "CVFHL "

@addToAmp
class Front_height_right_volume(_Channel_volume):
    name = "Front Height R Volume"
    function = "CVFHR "

@addToAmp
class Front_wide_left_volume(_Channel_volume):
    name = "Front Wide L Volume"
    function = "CVFWL "

@addToAmp
class Front_wide_right_volume(_Channel_volume):
    name = "Front Wide R Volume"
    function = "CVFWR "

class _Speaker_level(RelativeDecimal):
    category = "Speakers"
    call = "SSLEV ?"

@addToAmp
class Front_left_level(_Speaker_level): #undocumented
    function = "SSLEVFL "

@addToAmp
class Front_right_level(_Speaker_level): #undocumented
    function = "SSLEVFR "

@addToAmp
class Center_level(_Speaker_level): #undocumented
    function = "SSLEVC "

@addToAmp
class Subwoofer_level(_Speaker_level): #undocumented
    function = "SSLEVSW "
    
@addToAmp
class Surround_left_level(_Speaker_level): #undocumented
    function = "SSLEVSL "
    
@addToAmp
class Surround_right_level(_Speaker_level): #undocumented
    function = "SSLEVSR "
    
@addToAmp
class Surround_back_left_level(_Speaker_level): #undocumented
    name = "Surround Back L Level"
    function = "SSLEVSBL "
    
@addToAmp
class Surround_back_right_level(_Speaker_level): #undocumented
    name = "Surround Back R Level"
    function = "SSLEVSBR "
    
@addToAmp
class Surround_back_level(_Speaker_level): #undocumented
    function = "SSLEVSB "

@addToAmp
class Front_height_left_level(_Speaker_level): #undocumented
    name = "Front Height L Level"
    function = "SSLEVFHL "

@addToAmp
class Front_height_right_level(_Speaker_level): #undocumented
    name = "Front Height R Level"
    function = "SSLEVFHR "

@addToAmp
class Top_front_left_level(_Speaker_level): #undocumented
    name = "Top Front L Level"
    function = "SSLEVTFL "

@addToAmp
class Top_front_right_level(_Speaker_level): #undocumented
    name = "Top Front R Level"
    function = "SSLEVTFR "

@addToAmp
class Top_middle_left_level(_Speaker_level): #undocumented
    name = "Top Middle L Level"
    function = "SSLEVTML "

@addToAmp
class Top_middle_right_level(_Speaker_level): #undocumented
    name = "Top Middle R Level"
    function = "SSLEVTMR "

@addToAmp
class Front_atmos_left_level(_Speaker_level): #undocumented
    name = "Front Atmos L Level"
    function = "SSLEVFDL "

@addToAmp
class Front_atmos_right_level(_Speaker_level): #undocumented
    name = "Front Atmos R Level"
    function = "SSLEVFDR "

@addToAmp
class Surround_atmos_left_level(_Speaker_level): #undocumented
    name = "Surround Atmos L Level"
    function = "SSLEVSDL "

@addToAmp
class Surround_atmos_right_level(_Speaker_level): #undocumented
    name = "Surround Atmos R Level"
    function = "SSLEVSDR "

@addToAmp
class Main_zone_power(BoolFeature): function = "ZM"
    
@addToAmp
class Rec_select(SelectFeature): function = "SR"

@addToAmp
class Input_mode(SelectFeature):
    category = "Input"
    translation = {"AUTO":"Auto", "HDMI":"HDMI", "DIGITAL":"Digital", "ANALOG": "Analog"}
    function = "SD"

@addToAmp
class Digital_input(SelectFeature):
    category = "Input"
    function = "DC"
    translation = {"AUTO":"Auto", "PCM": "PCM", "DTS":"DTS"}
    
@addToAmp
class Video_select(SelectFeature):
    name = "Video Select Mode"
    category = "Video"
    function = "SV"
    translation = {"DVD":"DVD", "BD": "Blu-Ray", "TV":"TV", "SAT/CBL": "CBL/SAT", "DVR": "DVR", "GAME": "Game", "GAME2": "Game2", "V.AUX":"V.Aux", "DOCK": "Dock", "SOURCE":"cancel", "OFF":"Off"}

@addToAmp
class Sleep(IntFeature):
    min = 0 # 1..120, 0 will send "OFF"
    max = 120
    name = "Main Zone Sleep (minutes)"
    function = "SLP"
    def encodeVal(self, val): return "OFF" if val==0 else super().encodeVal(val)
    def decodeVal(self, val): return 0 if val=="OFF" else super().decodeVal(val)
    

@addToAmp
class Surround(SelectFeature):
    name = "Surround Mode"
    category = "Misc"
    function = "MS"
    translation = {"MOVIE":"Movie", "MUSIC":"Music", "GAME":"Game", "DIRECT": "Direct", "PURE DIRECT":"Pure Direct", "STEREO":"Stereo", "STANDARD": "Standard", "DOLBY DIGITAL":"Dolby Digital", "DTS SURROUND":"DTS Surround", "MCH STEREO":"Multi ch. Stereo", "ROCK ARENA":"Rock Arena", "JAZZ CLUB":"Jazz Club", "MONO MOVIE":"Mono Movie", "MATRIX":"Matrix", "VIDEO GAME":"Video Game", "VIRTUAL":"Virtual",
        "VIRTUAL:X":"DTS Virtual:X","NEURAL:X":"DTS Neural:X","DOLBY SURROUND":"Dolby Surround","M CH IN+DS":"Multi Channel In + Dolby S.", "M CH IN+NEURAL:X": "Multi Channel In + DTS Neural:X", "M CH IN+VIRTUAL:X":"Multi Channel In + DTS Virtual:X", "MULTI CH IN":"Multi Channel In", #undocumented
    }
    def matches(self, data): return super().matches(data) and not data.startswith("MSQUICK")
    def on_change(self, old, new):
        super().on_change(old,new)
        self.amp.send("CV?")


@addToAmp
class Quick_select(SelectFeature):
    name = "Quick Select (load)"
    function="MSQUICK"
    call="MSQUICK ?"
    translation = {"0":"(None)", **{str(n+1):str(n+1) for n in range(5)}}

@addToAmp
class Quick_select_store(amp.features.Constant, Quick_select):
    name = "Quick Select (save)"
    value = "(select)"
    def encode(self, value): return "QUICK%s MEMORY"%value

@addToAmp
class Hdmi_monitor(SelectFeature):
    name =" HDMI Monitor auto detection"
    category = "Video"
    function = "VSMONI"
    call = "VSMONI ?"
    translation = {"MONI1":"OUT-1", "MONI2":"OUT-2"}
    
@addToAmp
class Asp(SelectFeature):
    name = "ASP mode"
    function = "VSASP"
    call = "VSASP ?"
    translation = {"NRM":"Normal", "FUL":"Full"}
    
class _Resolution(SelectFeature):
    category = "Video"
    translation = {"48P":"480p/576p", "10I":"1080i", "72P":"720p", "10P":"1080p", "10P24":"1080p:24Hz", "AUTO":"Auto"}

@addToAmp
class Resolution(_Resolution):
    function = "VSSC"
    call = "VSSC ?"
    def matches(self, data): return super().matches(data) and not data.startswith("VSSCH")
    
@addToAmp
class Hdmi_resolution(_Resolution):
    name = "HDMI Resolution"
    function = "VSSCH"
    call = "VSSCH ?"

@addToAmp
class Hdmi_audio_output(SelectFeature):
    name = "HDMI Audio Output"
    category = "Video"
    function = "VSAUDIO "
    translation = {"AMP":"to Amp", "TV": "to TV"}
    
@addToAmp
class Video_processing_mode(SelectFeature):
    category = "Video"
    function = "VSVPM"
    call = "VSVPM ?"
    translation = {"AUTO":"Auto", "GAME":"Game", "MOVI": "Movie"}
    
@addToAmp
class Tone_control(BoolFeature):
    category = "Misc"
    function = "PSTONE CTRL "
    
@addToAmp
class Surround_back_mode(SelectFeature):
    name = "Surround Back SP Mode"
    function = "PSSB:"
    call = "PSSB: ?"
    translation = {"MTRX ON": "Matrix", "PL2x CINEMA":"Cinema", "PL2x MUSIC": "Music", "ON":"On", "OFF":"Off"}
    
@addToAmp
class Cinema_eq(BoolFeature):
    name = "Cinema Eq."
    function = "PSCINEMA EQ."
    call = "PSCINEMA EQ. ?"

@addToAmp
class Mode(SelectFeature):
    function = "PSMODE:"
    call = "PSMODE: ?"
    translation = {"MUSIC":"Music","CINEMA":"Cinema","GAME":"Game","PRO LOGIC":"Pro Logic"}
    
@addToAmp
class Front_height(BoolFeature):
    function = "PSFH:"
    call = "PSFH: ?"

@addToAmp
class Pl2hg(SelectFeature):
    name = "PL2z Height Gain"
    function = "PSPHG "
    translation = {"LOW":"Low","MID":"Medium","HI":"High"}
    
@addToAmp
class Speaker_output(SelectFeature):
    function = "PSSP:"
    call = "PSSP: ?"
    translation = {"FH":"F. Height", "FW":"F. Wide", "SB":"S. Back"}
    
@addToAmp
class Multi_eq(SelectFeature):
    name = "MultiEQ XT mode"
    category = "Audyssey"
    function = "PSMULTEQ:"
    call = "PSMULTEQ: ?"
    translation = {"AUDYSSEY":"Audyssey", "BYP.LR":"L/R Bypass", "FLAT":"Flat", "MANUAL":"Manual", "OFF":"Off"}
    
@addToAmp
class Dynamic_eq(BoolFeature):
    category = "Audyssey"
    function = "PSDYNEQ "
    
@addToAmp
class Reference_level(SelectFeature):
    category = "Audyssey"
    function = "PSREFLEV "
    translation = {"0":"0dB","5":"5dB","10":"10dB","15":"15dB"}
    
@addToAmp
class Dynamic_volume(SelectFeature):
    category = "Audyssey"
    function = "PSDYNVOL "
    translation = {"NGT":"Midnight", "EVE":"Evening", "DAY":"Day", "OFF":"Off"}
    
@addToAmp
class Audyssey_dsx(SelectFeature):
    name = "Audyssey DSX"
    category = "Audyssey"
    function = "PSDSX "
    translation = {"ONH":"On (Height)", "ONW":"On (Wide)","OFF":"Off"}
    
@addToAmp
class Stage_width(IntFeature): function = "PSSTW "

@addToAmp
class Stage_height(IntFeature): function = "PSSTH "
    
@addToAmp
class Bass(RelativeInt):
    category = "Misc"
    function = "PSBAS "
    
@addToAmp
class Treble(RelativeInt):
    category = "Misc"
    function = "PSTRE "
    
@addToAmp
class Drc(SelectFeature):
    function = "PSDRC "
    translation = {"AUTO":"Auto", "LOW":"Low", "MID":"Medium", "HI":"High", "OFF":"Off"}

@addToAmp
class Dynamic_compression(SelectFeature):
    function = "PSDCO "
    translation = {"LOW":"Low", "MID":"Medium", "HI":"High", "OFF":"Off"}

@addToAmp
class Lfe(IntFeature):
    name = "LFE"
    category = "Audio"
    function = "PSLFE "
    min=-10
    max=0
    def decodeVal(self, val): return super().decodeVal(val)*-1
    def encodeVal(self, val): return super().encodeVal(val*-1)

@addToAmp
class Effect_level(IntFeature): function = "PSEFF "
    
@addToAmp
class Delay(IntFeature):
    category = "Audio"
    max=999
    function = "PSDEL "
    
@addToAmp
class Afd(BoolFeature):
    name = "AFDM"
    function = "PSAFD "
    
@addToAmp
class Panorama(BoolFeature): function = "PSPAN "

@addToAmp
class Dimension(IntFeature): function = "PSDIM "

@addToAmp
class Center_width(IntFeature): function = "PSCEN "
    
@addToAmp
class Center_image(IntFeature): function = "PSCEI "
    
@addToAmp
class Subwoofer(BoolFeature):
    category = "Bass"
    function = "PSSWR "

class _Subwoofer_adjustment: #undocumented
    category = "Bass"
    #category = "Audio"
    function = "PSSWL "
    name = "Subwoofer Adjustment"

@addToAmp
class Subwoofer_adjustment_switch(_Subwoofer_adjustment, LooseBoolFeature): pass

@addToAmp
class Subwoofer_adjustment(_Subwoofer_adjustment, LooseDecimalFeature): pass

class _Dialog_level: #undocumented
    category = "Audio"
    function = "PSDIL "
    name = "Dialog Level"

@addToAmp
class Dialog_level_switch(_Dialog_level, LooseBoolFeature): pass

@addToAmp
class Dialog_level(_Dialog_level, LooseDecimalFeature): pass

@addToAmp
class Room_size(SelectFeature):
    function = "PSRSZ "
    translation = {e:e for e in ["S","MS","M","ML","L"]}
    
@addToAmp
class Audio_delay(IntFeature):
    category = "Audio"
    max = 999
    function  ="PSDELAY "

@addToAmp
class Restorer(SelectFeature):
    name = "Audio Restorer"
    category = "Audio"
    function = "PSRSTR "
    translation = {"OFF":"Off", "MODE1":"Mode 1", "MODE2":"Mode 2", "MODE3":"Mode 3"}
    
@addToAmp
class Front_speaker(SelectFeature):
    function = "PSFRONT"
    translation = {" SPA":"A"," SPB":"B"," A+B":"A+B"}
    
@addToAmp
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

@addToAmp
class Crossover_all(_Crossover): #undocumented
    name = "Crossover (all)"
    function = "SSCFRALL "
    
@addToAmp
class Crossover_front(_Crossover): #undocumented
    name = "Crossover (front)"
    function = "SSCFRFRO "
    
@addToAmp
class Crossover_surround(_Crossover): #undocumented
    name = "Crossover (surround)"
    function = "SSCFRSUA "

@addToAmp
class Crossover_center(_Crossover): #undocumented
    name = "Crossover (center)"
    function = "SSCFRCEN "

@addToAmp
class Crossover_surround_back(_Crossover): #undocumented
    name = "Crossover (surround back)"
    function = "SSCFRSBK "

@addToAmp
class Crossover_front_height(_Crossover): #undocumented
    name = "Crossover (front height)"
    function = "SSCFRFRH "

@addToAmp
class Crossover_top_front(_Crossover): #undocumented
    name = "Crossover (top front)"
    function = "SSCFRTFR "

@addToAmp
class Crossover_top_middle(_Crossover): #undocumented
    name = "Crossover (top middle)"
    function = "SSCFRTPM "

@addToAmp
class Crossover_front_atmos(_Crossover): #undocumented
    name = "Crossover (front atmos)"
    function = "SSCFRFRD "

@addToAmp
class Crossover_surround_atmos(_Crossover): #undocumented
    name = "Crossover (surround atmos)"
    function = "SSCFRSUD "

@addToAmp
class Subwoofer_mode(SelectFeature): #undocumented
    category = "Bass"
    function = "SSSWM "
    translation = {"L+M":"LFE + Main", "LFE":"LFE"}
    
@addToAmp
class Lfe_lowpass(SelectFeature): #undocumented
    name = "LFE Lowpass Freq."
    category = "Bass"
    function = "SSLFL "
    translation = {x:"%d Hz"%int(x) 
        for x in ["080","090","100","110","120","150","200","250"]}

@addToAmp
class Display(SelectFeature):
    function = "DIM "
    translation = {"BRI":"Bright","DIM":"Dim","DAR":"Dark","OFF":"Off"}

@addToAmp
class Input_signal(BoolFeature): #undocumented
    """ Value seems to indicate if amp is playing something via HDMI """
    function = "SSINFAISSIG "
    translation = {"01": False, "02": True}
    
    def async_poll(self, *args, **xargs): pass
    def matches(self, data): return super().matches(data) and isinstance(self.decode(data), bool)

@addToAmp
class Auto_standby(SelectFeature):
    category = "Eco"
    function = "STBY"
    translation = {"OFF":"Off","15M":"15 min","30M":"30 min","60M":"60 min"}


@addToAmp
class Amp_assign(SelectFeature): #undocumented
    category = "Speakers"
    function = "SSPAAMOD "
    call = "SSPAA ?"
    translation = {"FRB": "Front B", "BIA": "Bi-Amping", "NOR": "Surround Back", "FRH": "front height", "TFR": "Top Front", "TPM": "Top Middle", "FRD": "Front Dolby", "SUD": "Surround Dolby", **{"ZO%s"%zone:"Zone %s"%zone for zone in range(2,ZONES+1)}}


# TODO: implement PV

for zone in range(2,ZONES+1):
    
    class Zone:
        category = "Zone %s"%zone
    
    @addToAmp
    class ZVolume(Zone, Volume):
        name = "Zone %s Volume"%zone
        key = "zone%s_volume"%zone
        function = "Z%s"%zone
        call = "Z%s?"%zone
        
    @addToAmp
    class ZPower(Zone, BoolFeature):
        name = "Zone %s Power"%zone
        key = "zone%s_power"%zone
        function = "Z%s"%zone
        call = "Z%s?"%zone
        def matches(self, data): return super().matches(data) and data[len(self.function):] in self.translation
    
    @addToAmp
    class ZSource(Zone, Source):
        name = "Zone %s Source"%zone
        key = "zone%s_source"%zone
        function = "Z%s"%zone
        call = "Z%s?"%zone
        translation = {**Source.translation, "SOURCE": "Main Zone"}
        _from_mainzone = False
        
        def __init__(self, *args, **xargs):
            super().__init__(*args, **xargs)
            self.amp.features["source"].bind(on_change=lambda old,new:self._resolve_main_zone_source())

        def matches(self, data): return super().matches(data) and data[len(self.function):] in self.translation

        @amp.features.require("source")
        def _resolve_main_zone_source(self):
            if self._from_mainzone: super().store(self.amp.source)

        def store(self, data):
            self._from_mainzone = data == "Main Zone"
            if self._from_mainzone: self._resolve_main_zone_source()
            else: return super().store(data)
    
    @addToAmp
    class ZMuted(Zone, Muted):
        name = "Zone %s Muted"%zone
        key = "zone%s_muted"%zone
        function = "Z%sMU"%zone
    
    @addToAmp
    class Channel_setting(Zone, SelectFeature):
        key = "zone%s_channel_setting"%zone
        function = "Z%sCS"%zone
        translation = {"MONO":"Mono","ST":"Stereo"}
    
    @addToAmp
    class ZFrontLeftVolume(Zone, Front_left_volume):
        key = "zone%s_%s"%(zone, Front_left_volume.key)
        name = Front_left_volume.name
        function = "Z%sFL "%zone
        
    @addToAmp
    class ZFrontRightVolume(Zone, Front_right_volume):
        key = "zone%s_%s"%(zone, Front_right_volume.key)
        name = Front_right_volume.name
        function = "Z%sFR "%zone
        
    @addToAmp
    class Hpf(Zone, BoolFeature):
        key = "zone%s_hpf"%zone
        name = "HPF"
        function = "Z%sHPF"%zone
    
    @addToAmp
    class ZBass(Zone, RelativeInt):
        name = "Zone %s Bass"%zone
        key = "zone%s_bass"%zone
        function = "Z%sPSBAS "%zone
        
    @addToAmp
    class ZTreble(Zone, RelativeInt):
        name = "Zone %s Treble"%zone
        key = "zone%s_treble"%zone
        function = "Z%sPSTRE "%zone
        
    @addToAmp
    class Mdmi(Zone, SelectFeature):
        name = "MDMI Out"
        key = "zone%s_mdmi"%zone
        function = "Z%sHDA "%zone
        call = "z%sHDA?"%zone
        translation = {"THR":"THR", "PCM":"PCM"}
        
    @addToAmp
    class ZSleep(Zone, Sleep):
        name = "Zone %s Sleep (min.)"%zone
        key = "zone%s_sleep"%zone
        function = "Z%sSLP"%zone
        
    @addToAmp
    class Auto_Standby(Zone, SelectFeature):
        name = "Zone %s Auto Standby"%zone
        key = "zone%s_auto_standby"%zone
        function = "Z%sSTBY"%zone
        translation = {"2H":"2 hours","4H":"4 hours","8H":"8 hours","OFF":"Off"}


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
            key=None
            function=_function
            matches = lambda self, data: (matches(data) if matches else super().matches(data))
        _Feature.__name__ = _function
        return "%s%s"%(_function, _Feature(self).poll(force=True))
    
    def send(self, cmd): super().send(cmd.upper())


Amp = make_amp(features, DenonAmp)

