"""
Compatible with Denon Firmware Version 4600-6121-1061-3085
"""

import sys, math
from decimal import Decimal, InvalidOperation
from ..amp import TelnetAmp
from ..amp.features import require
from ..common.config import config
from .. import amp

ZONES = 4

SPEAKERS = [
    ('FL', 'front_left', 'Front Left'),
    ('FR', 'front_right', 'Front Right'),
    ('C', 'center', 'Center'),
    ('SW', 'subwoofer', 'Subwoofer'),
    ('SL', 'surround_left', 'Surround Left'),
    ('SR', 'surround_right', 'Surround Right'),
    ('SBL', 'surround_back_l', 'Surround Back L'),
    ('SBR', 'surround_back_r', 'Surround Back R'),
    ('SB', 'surround_back', 'Surround Back'),
    ('FHL', 'front_height_l', 'Front Height L'),
    ('FHR', 'front_height_r', 'Front Height R'),
    ('FWL', 'front_wide_l', 'Front Wide L'),
    ('FWR', 'front_wide_r', 'Front Wide R'),
    ('TFL', 'top_front_l', 'Top Front L'),
    ('TFR', 'top_front_r', 'Top Front R'),
    ('TML', 'top_middle_l', 'Top Middle L'),
    ('TMR', 'top_middle_r', 'Top Middle R'),
    ('FDL', 'front_atmos_l', 'Front Atmos L'),
    ('FDR', 'front_atmos_r', 'Front Atmos R'),
    ('SDL', 'surround_atmos_l', 'Surround Atmos L'),
    ('SDR', 'surround_atmos_r', 'Surround Atmos R'),
]

SOURCES = [
    ('PHONO', 'phono', 'Phono'),
    ('CD', 'cd', 'CD'),
    ('TUNER', 'tuner', 'Tuner'),
    ('DVD', 'dvd', 'DVD'),
    ('BD', 'bluray', 'Blu-ray'),
    ('TV', 'tv', 'TV'),
    ('SAT/CBL', 'cbl', 'CBL/SAT'),
    ('MPLAY', 'mediaplayer', 'Media Player'),
    ('GAME', 'game', 'Game'),
    ('HDRADIO', 'hdradio', 'HD Radio'),
    ('NET', 'heos', 'Heos'),
    ('PANDORA', 'pandora', 'Pandora'),
    ('SIRIUSXM', 'siriusxm', 'Sirius XM'),
    ('SPOTIFY', 'spotify', 'Spotify'),
    ('LASTFM', 'lastfm', 'Last FM'),
    ('FLICKR', 'flickr', 'Flickr'),
    ('IRADIO', 'iradio', 'IRadio'),
    ('SERVER', 'server', 'Server'),
    ('FAVORITES', 'favourites', 'Favourites'),
    ('AUX1', 'aux1', 'AUX 1'),
    ('AUX2', 'aux2', 'AUX 2'),
    ('AUX3', 'aux3', 'AUX 3'),
    ('AUX4', 'aux4', 'AUX 4'),
    ('AUX5', 'aux5', 'AUX 5'),
    ('AUX6', 'aux6', 'AUX 6'),
    ('AUX7', 'aux7', 'AUX 7'),
    ('BT', 'bluetooth', 'Bluetooth'),
    ('USB/IPOD', 'usbipod', 'USB/Ipod'),
    ('USB', 'usb', 'USB'),
    ('IPD', 'ipd', 'IPD'),
    ('IRP', 'irp', 'IRP'),
    ('FVP', 'fvp', 'FVP')
]

INPUTS = {
    ("ANA", "AN", "analog", "Analog"),
    ("DIN", "OP", "digital", "Digital"),
    ("VDO", "VD", "video", "Video"),
    ("HDM", "HD", "hdmi", "HDMI"),
}


class Amp(TelnetAmp):
    protocol = "Denon"
    preload_features = {"video_select"}
    
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
    
    def encodeVal(self, val): return super().encodeVal(val+50)
    def decodeVal(self, val): return super().decodeVal(val)-50
    

class RelativeDecimal(DecimalFeature):
    min = -12
    max = 12
    
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

@Amp.add_feature
class Volume(DecimalFeature):
    category = "Volume"
    function = "MV"
    def set(self, value, **xargs): super().set(min(max(self.min,value),self.max), **xargs)
    def matches(self, data): return data.startswith(self.function) and data[len(self.function):].isnumeric()
    
@Amp.add_feature
class Maxvol(DecimalFeature): #undocumented
    name = "Max. Vol."
    category = "Volume"
    function="MVMAX "
    call="MV?"
    default_value = 98
    def set(self, val, **xargs): raise RuntimeError("Cannot set MVMAX! Set '%s' instead."%VolumeLimit.name)

@Amp.add_feature
class VolumeLimit(SelectFeature): #undocumented
    category = "Volume"
    function="SSVCTZMALIM "
    call = "SSVCTZMA ?"
    translation = {"OFF":"Off", "060":"60", "070":"70", "080":"80"}
    def on_change(self, old, new):
        super().on_change(old, new)
        self.amp.features.maxvol.async_poll(force=True)

class _SpeakerConfig(SelectFeature):
    category = "Speakers"
    call = "SSSPC ?"
    translation = {"SMA":"Small","LAR":"Large","NON":"None"}

@Amp.add_feature
class Front_speaker_config(_SpeakerConfig): #undocumented
    function = "SSSPCFRO "
    
@Amp.add_feature
class Surround_speaker_config(_SpeakerConfig): #undocumented
    function = "SSSPCSUA "
    
@Amp.add_feature
class Center_speaker_config(_SpeakerConfig): #undocumented
    function = "SSSPCCEN "
    
@Amp.add_feature
class Surround_back_speaker_config(_SpeakerConfig): #undocumented
    function = "SSSPCSBK "
    
@Amp.add_feature
class Front_height_speaker_config(_SpeakerConfig): #undocumented
    function = "SSSPCFRH "
    
@Amp.add_feature
class Top_front_speaker_config(_SpeakerConfig): #undocumented
    function = "SSSPCTFR "
    
@Amp.add_feature
class Top_middle_speaker_config(_SpeakerConfig): #undocumented
    function = "SSSPCTPM "
    
@Amp.add_feature
class Front_atmos_speaker_config(_SpeakerConfig): #undocumented
    function = "SSSPCFRD "
    
@Amp.add_feature
class Surround_atmos_speaker_config(_SpeakerConfig): #undocumented
    function = "SSSPCSUD "
    
@Amp.add_feature
class Subwoofer_speaker_config(_SpeakerConfig): #undocumented
    function = "SSSPCSWF "
    translation = {"YES":"Yes","NO":"No"}
    
@Amp.add_feature
class Device_power(BoolFeature):
    category = "General"
    function = "PW"
    translation = {"ON":True,"STANDBY":False}

@Amp.add_feature
class Muted(BoolFeature):
    category = "Volume"
    function = "MU"


@Amp.add_feature
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
    default_value = {code: name for code, key, name in SOURCES}
    _ready = False
    
    def __init__(self, *args, **xargs):
        super().__init__(*args, **xargs)
        self.translation = self.translation.copy()
    def get(self): return "(select)"
    def set(self, *args, **xargs): raise RuntimeError("Cannot set value! Set source instead")
    def unset(self): self._ready = False
    def isset(self): return self._ready
    def encode(self, d):
        return "\n".join([f"{self.function}{code} {name}" for code, name in [*d.items(), ("","END")]])
    def decodeVal(self, x): return x
    def store(self, value):
        if value == self.default_value:
            self.translation = value.copy()
            self._ready = True
            super().store("0")
        elif value.strip() == "END":
            self._ready = True
            super().store("1") # cause self.on_change()
        else:
            try: code, name = value.split(" ",1)
            except:
                print(value)
                raise
            self.translation[code] = name
            super().store("2")


@Amp.add_feature
class Source(SelectFeature):
    category = "Input"
    function = "SI"
    translation = {"NET":"Heos", "BT":"Bluetooth", "USB":"USB"}
    
    def __init__(self, *args, **xargs):
        super().__init__(*args, **xargs)
        self.translation = self.translation.copy()
        self.amp.features.source_names.register_observer(self.on_source_names_change)

    def on_source_names_change(self, *args, **xargs):
        if self.isset():
            encoded = self.encode(self._val)
            self.translation.update(self.amp.features.source_names.translation)
            self.consume(encoded)
            self.on_change(self.get(), self.get()) # cause listeners to update from self.translation
        else:
            self.translation.update(self.amp.features.source_names.translation)
        
    @amp.features.require("source_names")
    def consume(self, data): return super().consume(data)
    
    @amp.features.require("source_names")
    def set(self, *args, **xargs): return super().set(*args, **xargs)


@Amp.add_feature(overwrite=True)
class Name(SelectFeature): #undocumented
    default_value = "Denon AVR"
    function = "NSFRN "
    def set(self, *args, **xargs): raise RuntimeError("Cannot set value!")

for code, key, name in SPEAKERS:
    @Amp.add_feature
    class Channel_volume(RelativeDecimal):
        name = f"{name} Volume"
        key = f"{key}_volume"
        category = "Volume"
        call = "CV?"
        function = f"CV{code} "

    @Amp.add_feature
    class Speaker_level(RelativeDecimal): #undocumented
        name = f"{name} Level"
        key = f"{key}_level"
        category = "Speakers"
        call = "SSLEV ?"
        function = f"SSLEV{code} "


@Amp.add_feature
class Main_zone_power(BoolFeature):
    key = "power"
    category = "General"
    function = "ZM"
    
@Amp.add_feature
class Rec_select(SelectFeature): function = "SR"

@Amp.add_feature
class Input_mode(SelectFeature):
    category = "Input"
    translation = {"AUTO":"Auto", "HDMI":"HDMI", "DIGITAL":"Digital", "ANALOG": "Analog"}
    function = "SD"

@Amp.add_feature
class Digital_input(SelectFeature):
    category = "Input"
    function = "DC"
    translation = {"AUTO":"Auto", "PCM": "PCM", "DTS":"DTS"}
    
@Amp.add_feature
class Video_select(SelectFeature):
    name = "Video Select Mode"
    category = "Video"
    function = "SV"
    translation = {"DVD":"DVD", "BD": "Blu-Ray", "TV":"TV", "SAT/CBL": "CBL/SAT", "DVR": "DVR", "GAME": "Game", "GAME2": "Game2", "V.AUX":"V.Aux", "DOCK": "Dock", "SOURCE":"cancel", "OFF":"Off"}

@Amp.add_feature
class Sleep(IntFeature):
    min = 0 # 1..120, 0 will send "OFF"
    max = 120
    name = "Main Zone Sleep (minutes)"
    function = "SLP"
    def encodeVal(self, val): return "OFF" if val==0 else super().encodeVal(val)
    def decodeVal(self, val): return 0 if val=="OFF" else super().decodeVal(val)
    

@Amp.add_feature
class SoundMode(SelectFeature):
    category = "General"
    function = "MS"
    translation = {"MOVIE":"Movie", "MUSIC":"Music", "GAME":"Game", "DIRECT": "Direct", "PURE DIRECT":"Pure Direct", "STEREO":"Stereo", "STANDARD": "Standard", "DOLBY DIGITAL":"Dolby Digital", "DTS SURROUND":"DTS Surround", "MCH STEREO":"Multi ch. Stereo", "ROCK ARENA":"Rock Arena", "JAZZ CLUB":"Jazz Club", "MONO MOVIE":"Mono Movie", "MATRIX":"Matrix", "VIDEO GAME":"Video Game", "VIRTUAL":"Virtual",
        "VIRTUAL:X":"DTS Virtual:X","NEURAL:X":"DTS Neural:X","DOLBY SURROUND":"Dolby Surround","M CH IN+DS":"Multi Channel In + Dolby S.", "M CH IN+NEURAL:X": "Multi Channel In + DTS Neural:X", "M CH IN+VIRTUAL:X":"Multi Channel In + DTS Virtual:X", "MULTI CH IN":"Multi Channel In", #undocumented
    }
    def matches(self, data): return super().matches(data) and not data.startswith("MSQUICK")
    def on_change(self, old, new):
        super().on_change(old,new)
        self.amp.send("CV?")


@Amp.add_feature
class QuickSelect(SelectFeature):
    name = "Quick Select (load)"
    function="MSQUICK"
    call="MSQUICK ?"
    translation = {"0":"(None)", **{str(n+1):str(n+1) for n in range(5)}}

@Amp.add_feature
class Quick_select_store(amp.features.Constant, QuickSelect):
    name = "Quick Select (save)"
    value = "(select)"
    def encode(self, value): return "QUICK%s MEMORY"%value

@Amp.add_feature
class Hdmi_monitor(SelectFeature):
    name =" HDMI Monitor auto detection"
    category = "Video"
    function = "VSMONI"
    call = "VSMONI ?"
    translation = {"MONI1":"OUT-1", "MONI2":"OUT-2"}
    
@Amp.add_feature
class Asp(SelectFeature):
    name = "ASP mode"
    function = "VSASP"
    call = "VSASP ?"
    translation = {"NRM":"Normal", "FUL":"Full"}
    
class _Resolution(SelectFeature):
    category = "Video"
    translation = {"48P":"480p/576p", "10I":"1080i", "72P":"720p", "10P":"1080p", "10P24":"1080p:24Hz", "AUTO":"Auto"}

@Amp.add_feature
class Resolution(_Resolution):
    function = "VSSC"
    call = "VSSC ?"
    def matches(self, data): return super().matches(data) and not data.startswith("VSSCH")
    
@Amp.add_feature
class Hdmi_resolution(_Resolution):
    name = "HDMI Resolution"
    function = "VSSCH"
    call = "VSSCH ?"

@Amp.add_feature
class Hdmi_audio_output(SelectFeature):
    name = "HDMI Audio Output"
    category = "Video"
    function = "VSAUDIO "
    translation = {"AMP":"to Amp", "TV": "to TV"}
    
@Amp.add_feature
class Video_processing_mode(SelectFeature):
    category = "Video"
    function = "VSVPM"
    call = "VSVPM ?"
    translation = {"AUTO":"Auto", "GAME":"Game", "MOVI": "Movie"}
    
@Amp.add_feature
class Tone_control(BoolFeature):
    category = "General"
    function = "PSTONE CTRL "
    
@Amp.add_feature
class Surround_back_mode(SelectFeature):
    name = "Surround Back SP Mode"
    function = "PSSB:"
    call = "PSSB: ?"
    translation = {"MTRX ON": "Matrix", "PL2x CINEMA":"Cinema", "PL2x MUSIC": "Music", "ON":"On", "OFF":"Off"}
    
@Amp.add_feature
class Cinema_eq(BoolFeature):
    name = "Cinema Eq."
    function = "PSCINEMA EQ."
    call = "PSCINEMA EQ. ?"

@Amp.add_feature
class Mode(SelectFeature):
    function = "PSMODE:"
    call = "PSMODE: ?"
    translation = {"MUSIC":"Music","CINEMA":"Cinema","GAME":"Game","PRO LOGIC":"Pro Logic"}
    
@Amp.add_feature
class Front_height(BoolFeature):
    function = "PSFH:"
    call = "PSFH: ?"

@Amp.add_feature
class Pl2hg(SelectFeature):
    name = "PL2z Height Gain"
    function = "PSPHG "
    translation = {"LOW":"Low","MID":"Medium","HI":"High"}
    
@Amp.add_feature
class Speaker_output(SelectFeature):
    function = "PSSP:"
    call = "PSSP: ?"
    translation = {"FH":"F. Height", "FW":"F. Wide", "SB":"S. Back"}
    
@Amp.add_feature
class Multi_eq(SelectFeature):
    name = "MultiEQ XT mode"
    category = "Audyssey"
    function = "PSMULTEQ:"
    call = "PSMULTEQ: ?"
    translation = {"AUDYSSEY":"Audyssey", "BYP.LR":"L/R Bypass", "FLAT":"Flat", "MANUAL":"Manual", "OFF":"Off"}
    
@Amp.add_feature
class Dynamic_eq(BoolFeature):
    category = "Audyssey"
    function = "PSDYNEQ "
    
@Amp.add_feature
class Reference_level(SelectFeature):
    category = "Audyssey"
    function = "PSREFLEV "
    translation = {"0":"0dB","5":"5dB","10":"10dB","15":"15dB"}
    
@Amp.add_feature
class Dynamic_volume(SelectFeature):
    category = "Audyssey"
    function = "PSDYNVOL "
    options = ["Off","Light","Medium","Heavy"]
    translation = {"LIT":"Light","MED":"Medium","HEV":"Heavy", #undocumented
        "NGT":"Heavy", "EVE":"Medium", "DAY":"Light","OFF":"Off"}
    
@Amp.add_feature
class Audyssey_dsx(SelectFeature):
    name = "Audyssey DSX"
    category = "Audyssey"
    function = "PSDSX "
    translation = {"ONH":"On (Height)", "ONW":"On (Wide)","OFF":"Off"}
    
@Amp.add_feature
class Stage_width(IntFeature): function = "PSSTW "

@Amp.add_feature
class Stage_height(IntFeature): function = "PSSTH "
    
@Amp.add_feature
class Bass(RelativeInt):
    category = "General"
    function = "PSBAS "
    
@Amp.add_feature
class Treble(RelativeInt):
    category = "General"
    function = "PSTRE "
    
@Amp.add_feature
class Drc(SelectFeature):
    function = "PSDRC "
    translation = {"AUTO":"Auto", "LOW":"Low", "MID":"Medium", "HI":"High", "OFF":"Off"}

@Amp.add_feature
class Dynamic_compression(SelectFeature):
    function = "PSDCO "
    translation = {"LOW":"Low", "MID":"Medium", "HI":"High", "OFF":"Off"}

@Amp.add_feature
class Lfe(IntFeature):
    name = "LFE"
    category = "Audio"
    function = "PSLFE "
    min=-10
    max=0
    def decodeVal(self, val): return super().decodeVal(val)*-1
    def encodeVal(self, val): return super().encodeVal(val*-1)

@Amp.add_feature
class Effect_level(IntFeature): function = "PSEFF "
    
@Amp.add_feature
class Delay(IntFeature):
    category = "Audio"
    max=999
    function = "PSDEL "
    
@Amp.add_feature
class Afd(BoolFeature):
    name = "AFDM"
    function = "PSAFD "
    
@Amp.add_feature
class Panorama(BoolFeature): function = "PSPAN "

@Amp.add_feature
class Dimension(IntFeature): function = "PSDIM "

@Amp.add_feature
class Center_width(IntFeature): function = "PSCEN "
    
@Amp.add_feature
class Center_image(IntFeature): function = "PSCEI "
    
@Amp.add_feature
class Subwoofer(BoolFeature):
    category = "Bass"
    function = "PSSWR "

class _Subwoofer_adjustment: #undocumented
    category = "Bass"
    #category = "Audio"
    function = "PSSWL "
    name = "Subwoofer Adjustment"

@Amp.add_feature
class Subwoofer_adjustment_switch(_Subwoofer_adjustment, LooseBoolFeature): pass

@Amp.add_feature
class Subwoofer_adjustment(_Subwoofer_adjustment, LooseDecimalFeature): pass

class _Dialog_level: #undocumented
    category = "Audio"
    function = "PSDIL "
    name = "Dialog Level"

@Amp.add_feature
class Dialog_level_switch(_Dialog_level, LooseBoolFeature): pass

@Amp.add_feature
class Dialog_level(_Dialog_level, LooseDecimalFeature): pass

@Amp.add_feature
class Room_size(SelectFeature):
    function = "PSRSZ "
    translation = {e:e for e in ["S","MS","M","ML","L"]}
    
@Amp.add_feature
class Audio_delay(IntFeature):
    category = "Audio"
    max = 999
    function  ="PSDELAY "

@Amp.add_feature
class Restorer(SelectFeature):
    name = "Audio Restorer"
    category = "Audio"
    function = "PSRSTR "
    translation = {"OFF":"Off", "MODE1":"Mode 1", "MODE2":"Mode 2", "MODE3":"Mode 3"}
    
@Amp.add_feature
class Front_speaker(SelectFeature):
    function = "PSFRONT"
    translation = {" SPA":"A"," SPB":"B"," A+B":"A+B"}
    
@Amp.add_feature
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

@Amp.add_feature
class Crossover_all(_Crossover): #undocumented
    name = "Crossover (all)"
    function = "SSCFRALL "
    
@Amp.add_feature
class Crossover_front(_Crossover): #undocumented
    name = "Crossover (front)"
    function = "SSCFRFRO "
    
@Amp.add_feature
class Crossover_surround(_Crossover): #undocumented
    name = "Crossover (surround)"
    function = "SSCFRSUA "

@Amp.add_feature
class Crossover_center(_Crossover): #undocumented
    name = "Crossover (center)"
    function = "SSCFRCEN "

@Amp.add_feature
class Crossover_surround_back(_Crossover): #undocumented
    name = "Crossover (surround back)"
    function = "SSCFRSBK "

@Amp.add_feature
class Crossover_front_height(_Crossover): #undocumented
    name = "Crossover (front height)"
    function = "SSCFRFRH "

@Amp.add_feature
class Crossover_top_front(_Crossover): #undocumented
    name = "Crossover (top front)"
    function = "SSCFRTFR "

@Amp.add_feature
class Crossover_top_middle(_Crossover): #undocumented
    name = "Crossover (top middle)"
    function = "SSCFRTPM "

@Amp.add_feature
class Crossover_front_atmos(_Crossover): #undocumented
    name = "Crossover (front atmos)"
    function = "SSCFRFRD "

@Amp.add_feature
class Crossover_surround_atmos(_Crossover): #undocumented
    name = "Crossover (surround atmos)"
    function = "SSCFRSUD "

@Amp.add_feature
class Subwoofer_mode(SelectFeature): #undocumented
    category = "Bass"
    function = "SSSWM "
    translation = {"L+M":"LFE + Main", "LFE":"LFE"}
    
@Amp.add_feature
class Lfe_lowpass(SelectFeature): #undocumented
    name = "LFE Lowpass Freq."
    category = "Bass"
    function = "SSLFL "
    translation = {x:"%d Hz"%int(x) 
        for x in ["080","090","100","110","120","150","200","250"]}

@Amp.add_feature
class Display(SelectFeature):
    function = "DIM "
    translation = {"BRI":"Bright","DIM":"Dim","DAR":"Dark","OFF":"Off"}

@Amp.add_feature
class Input_signal(BoolFeature): #undocumented
    """
    Information on Audio Input Signal
    Value seems to indicate if amp is playing something via HDMI
    """
    category = "Input"
    function = "SSINFAISSIG "
    translation = {"01": False, "02": True} #01: analog, 02: PCM
    
    def __init__(self, *args, **xargs):
        super().__init__(*args, **xargs)
        self.amp.bind(on_stop_playing = self.on_stop_playing)
        
    def async_poll(self, *args, **xargs): pass

    def matches(self, data): return super().matches(data) and isinstance(self.decode(data), bool)

    def on_change(self, old, new):
        super().on_change(old, new)
        self.amp.on_start_playing() if new == True else self.amp.on_stop_playing()

    @require("input_signal")
    def on_stop_playing(self):
        # undo amp.on_stop_playing() if self.get() == True
        if self.get(): self.amp.on_start_playing()


@Amp.add_feature
class Sample_rate(SelectFeature): #undocumented
    """ Information on Audio Input Signal Sample Rate """
    category = "Input"
    function = "SSINFAISFV "


@Amp.add_feature
class Auto_standby(SelectFeature):
    category = "Eco"
    function = "STBY"
    translation = {"OFF":"Off","15M":"15 min","30M":"30 min","60M":"60 min"}


@Amp.add_feature
class Amp_assign(SelectFeature): #undocumented
    category = "Speakers"
    function = "SSPAAMOD "
    call = "SSPAA ?"
    translation = {"FRB": "Front B", "BIA": "Bi-Amping", "NOR": "Surround Back", "FRH": "Front Height", "TFR": "Top Front", "TPM": "Top Middle", "FRD": "Front Dolby", "SUD": "Surround Dolby", **{"ZO%s"%zone:"Zone %s"%zone for zone in range(2,ZONES+1)}}


@Amp.add_feature
class Volume_osd(SelectFeature): #undocumented
    category = "Video"
    function = "SSOSDVOL "
    translation = {"TOP":"Top","BOT":"Bottom","OFF":"Off"}


@Amp.add_feature
class Info_osd(BoolFeature): #undocumented
    category = "Video"
    function = "SSOSDTXT "


@Amp.add_feature
class Hdmi_rc_select(SelectFeature): #undocumented
    function = "SSHOSRSS "
    translation = {"POS":"Power On + Source", "SSO":"Only Source"}


@Amp.add_feature
class Hdmi_control(SelectFeature): #undocumented
    function = "SSHOSCON "
    call = "SSHOS ?"
    translation = {"ON":"On","OFF":"Off"}


@Amp.add_feature
class Language(SelectFeature): #undocumented
    function = "SSLAN "
    translation = {"DEU":"German", "ENG":"English", "ESP":"Spanish", "POL":"Polish", "RUS": "Russian",
        "FRA":"French", "ITA":"Italian", "NER":"Dutch", "SVE":"Swedish"}


@Amp.add_feature
class Eco_mode(SelectFeature): #undocumented
    category = "Eco"
    function = "ECO"
    translation = {"AUTO":"Auto","ON":"On","OFF":"Off"}


for code, key, name in SOURCES:
    @Amp.add_feature
    class InputVisibility(BoolFeature): #undocumented
        name = f"Enable {name} Input"
        key = f"enable_{key}"
        category = "Input"
        call = "SSSOD ?"
        function = f"SSSOD{code} "
        translation = {"USE":True, "DEL":False}


for code, key, name in SOURCES:
    @Amp.add_feature
    class SourceVolumeLevel(RelativeInt): #undocumented
        name = f"{name} Volume Level"
        key = f"{key}_volume_level"
        category = "Input"
        min = -12
        max = 12
        call = "SSSLV ?"
        function = f"SSSLV{code} "
        def set(self, *args, **xargs):
            super().set(*args, **xargs)
            self.async_poll(force=True) #Denon workaround: missing echo


for code, key, name in SPEAKERS:
    @Amp.add_feature
    class SpeakerDistance(IntFeature): #undocumented
        name = f"{name} Distance"
        key = f"{key}_distance"
        category = "Speakers"
        min = 0
        max = 1800
        call = "SSSDE ?"
        function = f"SSSDE{code} "


@Amp.add_feature
class Serial_number(SelectFeature):
    call = "VIALL?"
    function = "VIALLS/N."


@Amp.add_feature
class Volume_scale(SelectFeature):
    category = "Volume"
    function = "SSVCTZMADIS "
    call = "SSVCTZMA ?"
    translation = {"REL":"-79-18 dB", "ABS":"0-98"}


@Amp.add_feature
class Power_on_level(LooseIntFeature):
    category = "Volume"
    key = "power_on_level_numeric"
    function = "SSVCTZMAPON "
    call = "SSVCTZMA ?"


@Amp.add_feature
class Power_on_level(SelectFeature):
    category = "Volume"
    function = "SSVCTZMAPON "
    call = "SSVCTZMA ?"
    translation = {"MUT":"Muted", "LAS":"Unchanged"}
    def on_change(self, val, prev):
        super().on_change(val, prev)
        if not self.amp.features.power_on_level_numeric.isset():
            self.amp.features.power_on_level_numeric.store(0)


@Amp.add_feature
class Mute(SelectFeature):
    category = "Volume"
    function = "SSVCTZMAMLV "
    call = "SSVCTZMA ?"
    translation = {"MUT":"Full", "040":"-40 dB", "060":"-20 dB"}


for source_code, source_key, source_name in SOURCES:
    for input_code, input_value_code, input_key, input_name in INPUTS:
        @Amp.add_feature
        class SourceInputAssign(SelectFeature):
            name = f"{source_name} {input_name} Input"
            key = f"input_{source_key}_{input_key}"
            category = "Input"
            function = f"SS{input_code}{source_code} "
            call = f"SS{input_code} ?"
            translation = {"OFF":"None", "FRO":"Front",
                **{f"{input_value_code}{i}":f"{input_name} {i}" for i in range(7)}}


# TODO: implement PV

for zone in range(2,ZONES+1):
    
    class Zone:
        category = "Zone %s"%zone
    
    @Amp.add_feature
    class ZVolume(Zone, Volume):
        name = "Zone %s Volume"%zone
        key = "zone%s_volume"%zone
        function = "Z%s"%zone
        
    @Amp.add_feature
    class ZPower(Zone, BoolFeature):
        name = "Zone %s Power"%zone
        key = "zone%s_power"%zone
        function = "Z%s"%zone
        def matches(self, data): return super().matches(data) and data[len(self.function):] in self.translation
    
    @Amp.add_feature
    class ZSource(Zone, Source):
        name = "Zone %s Source"%zone
        key = "zone%s_source"%zone
        function = "Z%s"%zone
        translation = {**Source.translation, "SOURCE": "Main Zone"}
        _from_mainzone = False
        
        def __init__(self, *args, **xargs):
            super().__init__(*args, **xargs)
            self.amp.features.source.register_observer(lambda *_:self._resolve_main_zone_source())

        def matches(self, data): return super().matches(data) and data[len(self.function):] in self.translation

        @amp.features.require("source")
        def _resolve_main_zone_source(self):
            if self._from_mainzone: super().store(self.amp.source)

        def store(self, data):
            self._from_mainzone = data == "Main Zone"
            if self._from_mainzone: self._resolve_main_zone_source()
            else: return super().store(data)
        
        def unset(self):
            super().unset()
            self._from_mainzone = False
    
    @Amp.add_feature
    class ZMuted(Zone, Muted):
        name = "Zone %s Muted"%zone
        key = "zone%s_muted"%zone
        function = "Z%sMU"%zone
    
    @Amp.add_feature
    class Channel_setting(Zone, SelectFeature):
        key = "zone%s_channel_setting"%zone
        function = "Z%sCS"%zone
        translation = {"MONO":"Mono","ST":"Stereo"}
    
    @Amp.add_feature
    class ZFrontLeftVolume(Zone, RelativeDecimal):
        key = "zone%s_front_left_volume"%zone
        name = "Front Left Volume"
        function = "Z%sFL "%zone
        call = "Z%sCV?"%zone
        
    @Amp.add_feature
    class ZFrontRightVolume(Zone, RelativeDecimal):
        key = "zone%s_front_right_volume"%zone
        name = "Front Right Volume"
        function = "Z%sFR "%zone
        call = "Z%sCV?"%zone
        
    @Amp.add_feature
    class Hpf(Zone, BoolFeature):
        key = "zone%s_hpf"%zone
        name = "HPF"
        function = "Z%sHPF"%zone
    
    @Amp.add_feature
    class ZBass(Zone, RelativeInt):
        name = "Zone %s Bass"%zone
        key = "zone%s_bass"%zone
        function = "Z%sPSBAS "%zone
        
    @Amp.add_feature
    class ZTreble(Zone, RelativeInt):
        name = "Zone %s Treble"%zone
        key = "zone%s_treble"%zone
        function = "Z%sPSTRE "%zone
        
    @Amp.add_feature
    class Mdmi(Zone, SelectFeature):
        name = "MDMI Out"
        key = "zone%s_mdmi"%zone
        function = "Z%sHDA "%zone
        call = "Z%sHDA?"%zone
        translation = {"THR":"THR", "PCM":"PCM"}
        
    @Amp.add_feature
    class ZSleep(Zone, Sleep):
        name = "Zone %s Sleep (min.)"%zone
        key = "zone%s_sleep"%zone
        function = "Z%sSLP"%zone
        
    @Amp.add_feature
    class Auto_Standby(Zone, SelectFeature):
        name = "Zone %s Auto Standby"%zone
        key = "zone%s_auto_standby"%zone
        function = "Z%sSTBY"%zone
        translation = {"2H":"2 hours","4H":"4 hours","8H":"8 hours","OFF":"Off"}

