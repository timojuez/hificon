"""
Compatible with Denon Firmware Version 4600-6121-1061-3085
"""

import sys, math
from urllib.parse import urlparse
from threading import Timer
from decimal import Decimal, InvalidOperation
from ..core import features, TelnetScheme
from ..core.transmission.types import ClientType, ServerType


ZONES = [2, 3, 4]

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

SPEAKERS_2 = [
    ('FL', 'front_left', 'Front Left'),
    ('FR', 'front_right', 'Front Right'),
    ('CEN', 'center', 'Center'),
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

SPEAKER_PAIRS = [
    ("FRO", "front", "Front"),
    ("SUA", "surround", "Surround"),
    ("CEN", "center", "Center"),
    ("SBK", "surround_back", "Surround Back"),
    ("FRH", "front_height", "Front Height"),
    ("TFR", "top_front", "Top Front"),
    ("TPM", "top_middle", "Top Middle"),
    ("FRD", "front_atmos", "Front Atmos"),
    ("SUD", "surround_atmos", "Surround Atmos"),
]

SPEAKER_PAIRS_2 = [
    ("FRO", "front", "Front"),
    ("SUR", "surround", "Surround"),
    ("CEN", "center", "Center"),
    ("SBK", "surround_back", "Surround Back"),
    ("FRH", "front_height", "Front Height"),
    ("TFR", "top_front", "Top Front"),
    ("TPM", "top_middle", "Top Middle"),
    ("FRD", "front_atmos", "Front Atmos"),
    ("SUD", "surround_atmos", "Surround Atmos"),
]

EQ_BOUNDS = ["63 Hz", "125 Hz", "250 Hz", "500 Hz", "1 kHz", "2 kHz", "4 kHz", "8 kHz", "16 kHz"]

EQ_OPTIONS = [
    ("ALL", "all", "All Channels", [("ALL", "all", "(all ch.)")]),
    ("LRS", "lr", "Left+Right", SPEAKER_PAIRS_2),
    ("EAC", "channel", "Each Channel", SPEAKERS_2)
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

Category = type("Category", tuple(), dict(
    GENERAL = "General",
    VOLUME = "Volume",
    INPUT = "Input",
    SPEAKERS = "Speakers",
    AUDIO = "Audio",
    VIDEO = "Video",
    BASS = "Bass",
    EQUALIZER = "Equalizer",
    AUDYSSEY = "Audyssey",
    ECO = "Eco",
    **{f"ZONE_{zone}": f"Zone {zone}" for zone in ZONES}
))


class Denon(TelnetScheme):
    description = "Denon/Marantz AVR compatible (tested with Denon X1400H)"
    _pulse = "CV?" # workaround for denon to retrieve CV?
    
    @classmethod
    def new_client_by_ssdp(cls, response, *args, **xargs):
        if "denon" in response.st.lower() or "marantz" in response.st.lower():
            host = urlparse(response.location).hostname
            port = 23 # TODO
            return cls.new_client(host, port, *args, **xargs)

    def query(self, cmd, matches=None):
        """
        Send command to target
        @cmd str: function[?|param]
        @matches callable: return received line where matches(line) is True
        """
        _function = cmd.upper().replace("?","")
        if "?" not in cmd: return self.send(cmd)
        class _Feature(SelectFeature):
            id=None
            function=_function
            matches = lambda self, data: (matches(data) if matches else super().matches(data))
        _Feature.__name__ = _function
        f = _Feature(self)
        f.wait_poll(force=True)
        return "%s%s"%(_function, f.get())
    
    def send(self, cmd): super().send(cmd.upper() if cmd == cmd.lower() else cmd)


class DenonFeature:
    """ Handles Denon format "@function@value" """
    
    function = None #str, Denon function command
    call = property(lambda self: "%s?"%self.function)
    
    def serialize(self, value):
        return "%s%s"%(self.function, self.serialize_val(value))
    
    def serialize_val(self, value): return value

    def unserialize(self, cmd):
        param = cmd[len(self.function):]
        return self.unserialize_val(param)

    def unserialize_val(self, data): return data
        
    def matches(self, cmd):
        return cmd.startswith(self.function) #and " " not in cmd.replace(self.function,"",1)
    
        
class _Translation:
    translation = {} #{return_string:value} unserialize return_string to value / serialize vice versa

    options = property(lambda self: list(self.translation.values()))
    
    def unserialize_val(self, val): return self.translation.get(val,val)
        
    def serialize_val(self, val):
        return {val:key for key,val in self.translation.items()}.get(val,val)


######### Data Types

class SelectFeature(_Translation, DenonFeature, features.SelectFeature): pass

class NumericFeature(DenonFeature):
    """ add UP/DOWN value decoding capability """
    step = 1

    def unserialize_val(self, val):
        if val == "UP": return self.get()+self.step
        elif val == "DOWN": return self.get()-self.step
        else: raise ValueError(f"Invalid value `{val}` for feature `{self.id}`")


class DecimalFeature(NumericFeature, features.DecimalFeature):
    step = Decimal('.5')
    min = 0
    max = 98

    def __str__(self): return "%0.1f"%self.get() if self.isset() else super().__str__()

    @classmethod
    def _roundVolume(self, vol): return self.step*round(vol/self.step)

    def unserialize_val(self, val):
        return Decimal(val.ljust(3,"0"))/10 if val.isnumeric() else super().unserialize_val(val)

    def serialize_val(self, val):
        val = self._roundVolume(val)
        return "%02d"%val if val%1 == 0 else "%03d"%(val*10)


class IntFeature(NumericFeature, features.IntFeature):
    
    def serialize_val(self, val):
        longestValue = max(abs(self.max),abs(self.min))
        digits = math.ceil(math.log(longestValue+1,10))
        return ("%%0%dd"%digits)%val
    
    def unserialize_val(self, val):
        return int(val) if val.isnumeric() else super().unserialize_val(val)


class BoolFeature(_Translation, DenonFeature, features.BoolFeature):
    translation = {"ON":True,"OFF":False}
    

class RelativeInt(IntFeature):
    min = -6
    max = 6

    def serialize_val(self, val): return super().serialize_val(val+50)

    def unserialize_val(self, val):
        return super().unserialize_val(val)-50 if val.isnumeric() else super().unserialize_val(val)


class RelativeDecimal(DecimalFeature):
    min = -12
    max = 12

    def serialize_val(self, val): return super().serialize_val(val+50)

    def unserialize_val(self, val):
        return super().unserialize_val(val)-50 if val.isnumeric() else super().unserialize_val(val)


class _LooseNumericFeature:
    """ Value where the target does not always send a numeric """
    
    def matches(self, data):
        try:
            assert(super().matches(data))
            self.unserialize(data)
            return True
        except (TypeError, ValueError, AssertionError, InvalidOperation): return False


class LooseDecimalFeature(_LooseNumericFeature, RelativeDecimal): pass

class LooseIntFeature(_LooseNumericFeature, IntFeature): pass

class LooseBoolFeature(BoolFeature):
    """ Value where the target does not always send a boolean """

    def matches(self,data):
        return super().matches(data) and isinstance(self.unserialize(data), bool)

    def on_change(self, val):
        super().on_change(val)
        if val == True: self.target.send(self.call) # make target send the nonbool value TODO: only once



class MultipartFeatureMixin(features.MultipartFeatureMixin, DenonFeature, features.Feature):
    TERMINATOR = "END"
    def to_parts(self, val): raise NotImplementedError()
    def from_parts(self, l): raise NotImplementedError()
    def is_complete(self, l): return l[-1] == super().serialize(self.TERMINATOR)
    def serialize(self, value):
        return [super(MultipartFeatureMixin, self).serialize(e)
            for e in [*self.to_parts(value), self.TERMINATOR]]
    def unserialize(self, l):
        return self.from_parts([super(MultipartFeatureMixin, self).unserialize(e)
            for e in l[:-1]])


######### Features implementation (see Denon CLI protocol)

@Denon.add_feature(overwrite=True)
class Fallback(Denon.features.fallback):
    """ hide known messages from AVR """
    name = Denon.features.fallback.name

    def consume(self, data):
        if not data.endswith("END"): return super().consume(data)


@Denon.add_feature
class Volume(DecimalFeature):
    category = Category.VOLUME
    function = "MV"

    def matches(self, data): return data.startswith(self.function) and (
        data[len(self.function):].isnumeric() or data[len(self.function):] in ["UP", "DOWN"])


@Denon.add_feature
class Maxvol(DecimalFeature): #undocumented
    name = "Max. Vol."
    category = Category.VOLUME
    function="MVMAX "
    call="MV?"
    default_value = 98
    def remote_set(self, val, **xargs): raise RuntimeError("Cannot set MVMAX! Set '%s' instead."%VolumeLimit.name)

@Denon.add_feature
class VolumeLimit(SelectFeature): #undocumented
    category = Category.VOLUME
    function="SSVCTZMALIM "
    call = "SSVCTZMA ?"
    translation = {"OFF":"Off", "060":"60", "070":"70", "080":"80"}
    def on_change(self, val):
        super().on_change(val)
        self.target.features.maxvol.async_poll(force=True)

class _SpeakerConfig(SelectFeature):
    category = Category.SPEAKERS
    call = "SSSPC ?"
    translation = {"SMA":"Small","LAR":"Large","NON":"None"}

@Denon.add_feature
class FrontSpeakerConfig(_SpeakerConfig): #undocumented
    function = "SSSPCFRO "
    
@Denon.add_feature
class SurroundSpeakerConfig(_SpeakerConfig): #undocumented
    function = "SSSPCSUA "
    
@Denon.add_feature
class CenterSpeakerConfig(_SpeakerConfig): #undocumented
    function = "SSSPCCEN "
    
@Denon.add_feature
class SurroundBackSpeakerConfig(_SpeakerConfig): #undocumented
    function = "SSSPCSBK "
    
@Denon.add_feature
class FrontHeightSpeakerConfig(_SpeakerConfig): #undocumented
    function = "SSSPCFRH "
    
@Denon.add_feature
class TopFrontSpeakerConfig(_SpeakerConfig): #undocumented
    function = "SSSPCTFR "
    
@Denon.add_feature
class TopMiddleSpeakerConfig(_SpeakerConfig): #undocumented
    function = "SSSPCTPM "
    
@Denon.add_feature
class FrontAtmosSpeakerConfig(_SpeakerConfig): #undocumented
    function = "SSSPCFRD "
    
@Denon.add_feature
class SurroundAtmosSpeakerConfig(_SpeakerConfig): #undocumented
    function = "SSSPCSUD "
    
@Denon.add_feature
class SubwooferSpeakerConfig(_SpeakerConfig): #undocumented
    function = "SSSPCSWF "
    translation = {"YES":"Yes","NO":"No"}
    
@Denon.add_feature
class DevicePower(BoolFeature):
    category = Category.GENERAL
    function = "PW"
    translation = {"ON":True,"STANDBY":False}

@Denon.add_feature
class Muted(BoolFeature):
    category = Category.VOLUME
    function = "MU"

@Denon.add_feature
class SourceNames(MultipartFeatureMixin): #undocumented
    """
    SSFUN ?
    SSFUNSAT/CBL CBL/SAT
    SSFUNMPLAY Media Player
    SSFUN END    
    """
    category = Category.INPUT
    type = dict
    TERMINATOR = " END"
    function = "SSFUN"
    call = "SSFUN ?"
    default_value = {code: name for code, f_id, name in SOURCES}
    def remote_set(self, *args, **xargs): raise RuntimeError("Cannot set value! Set source instead")
    def to_parts(self, d): return [" ".join(e) for e in d.items()]
    def from_parts(self, l): return dict([line.split(" ",1) for line in l])

@Denon.add_feature
class Source(SelectFeature):
    category = Category.INPUT
    function = "SI"
    translation = {"NET":"Heos", "BT":"Bluetooth", "USB":"USB"}
    
    def __init__(self, *args, **xargs):
        super().__init__(*args, **xargs)
        self.translation = self.translation.copy()
        self.target.features.source_names.bind(self.on_source_names_change)

    def on_source_names_change(self, source_names):
        with self._lock:
            if self.isset():
                old = self.serialize(self._val)
                self.translation.update(source_names)
                self._val = self.unserialize(old)
                self.on_change(self._val) # cause listeners to update from self.translation
            else:
                self.translation.update(source_names)
        
    def consume(self, data):
        self.target.schedule(lambda *_: super(Source, self).consume(data), requires=("source_names",))
    
    def _remote_set(self, *args, **xargs):
        super(Source, self).remote_set(*args, **xargs)
        self.async_poll()

    def remote_set(self, *args, **xargs):
        self.target.schedule(lambda *_: self._remote_set(*args, **xargs), requires=("source_names",))


@Denon.add_feature(overwrite=True)
class Name(features.ServerToClientFeatureMixin, SelectFeature): #undocumented
    default_value = "Denon AVR"
    dummy_value = "Dummy X7800H"
    function = "NSFRN "


for code, f_id, name in SPEAKERS:
    @Denon.add_feature
    class ChannelVolume(RelativeDecimal):
        name = f"{name} Volume"
        id = f"{f_id}_volume"
        category = Category.VOLUME
        call = "CV?"
        function = f"CV{code} "

    @Denon.add_feature
    class SpeakerLevel(RelativeDecimal): #undocumented
        name = f"{name} Level"
        id = f"{f_id}_level"
        category = Category.SPEAKERS
        call = "SSLEV ?"
        function = f"SSLEV{code} "


@Denon.add_feature
class MainZonePower(BoolFeature):
    id = "power"
    category = Category.GENERAL
    function = "ZM"
    
@Denon.add_feature
class RecSelect(SelectFeature): function = "SR"

@Denon.add_feature
class InputMode(SelectFeature):
    category = Category.INPUT
    translation = {"AUTO":"Auto", "HDMI":"HDMI", "DIGITAL":"Digital", "ANALOG": "Analog"}
    function = "SD"

@Denon.add_feature
class DigitalInput(SelectFeature):
    category = Category.INPUT
    function = "DC"
    translation = {"AUTO":"Auto", "PCM": "PCM", "DTS":"DTS"}
    
@Denon.add_feature
class VideoSelect(SelectFeature):
    name = "Video Select Mode"
    category = Category.VIDEO
    function = "SV"
    translation = {"DVD":"DVD", "BD": "Blu-Ray", "TV":"TV", "SAT/CBL": "CBL/SAT", "DVR": "DVR", "GAME": "Game", "GAME2": "Game2", "V.AUX":"V.Aux", "DOCK": "Dock", "SOURCE":"cancel", "OFF":"Off"}

@Denon.add_feature
class Sleep(IntFeature):
    min = 0 # 1..120, 0 will send "OFF"
    max = 120
    name = "Main Zone Sleep (minutes)"
    function = "SLP"
    def serialize_val(self, val): return "OFF" if val==0 else super().serialize_val(val)
    def unserialize_val(self, val): return 0 if val=="OFF" else super().unserialize_val(val)

@Denon.add_feature
class SoundMode(SelectFeature): #undocumented
    category = Category.GENERAL
    function = "SSSMG "
    translation = {"MOV":"Movie", "MUS":"Music", "GAM":"Game", "PUR":"Pure"}
    translation_inv = {"Movie":"MSMOVIE", "Music":"MSMUSIC", "Game":"MSGAME", "Pure":"MSDIRECT"}
    
    def serialize(self, value):
        return self.translation_inv[value] if isinstance(self.target, ClientType) else super().serialize(value)

    def on_change(self, val):
        super().on_change(val)
        self.target.features.sound_mode_setting.async_poll(force=True)
        self.target.features.sound_mode_settings.async_poll(force=True)


@Denon.add_feature
class SoundModeSettings(MultipartFeatureMixin): # according to current sound mode #undocumented
    category = Category.GENERAL
    type = dict
    function = 'OPSML '
    dummy_value = {"010":"Stereo", "020":"Dolby Surround", "030":"DTS Neural:X", "040":"DTS Virtual:X", "050":"Multi Ch Stereo", "061":"Mono Movie", "070":"Virtual"}

    def to_parts(self, d):
        return ["".join([key[:2], str(int(self.target.features.sound_mode_setting.get() == val)), val])
            for key, val in d.items()]

    def resend(self):
        self.target.schedule(lambda f: super(SoundModeSettings, self).resend(),
            requires=("sound_mode_setting",))

    def remote_set(self, *args, **xargs):
        self.target.schedule(lambda f: super(SoundModeSettings, self).remote_set(*args, **xargs),
            requires=("sound_mode_setting",))

    def from_parts(self, l): return {data[:3]: data[3:] for data in l}


@Denon.add_feature
class SoundModeSetting(SelectFeature):
    category = Category.GENERAL
    function = 'OPSML '
    dummy_value = "Stereo"

    def __init__(self, *args, **xargs):
        super().__init__(*args, **xargs)
        self.target.features.sound_mode_settings.bind(self.on_sound_modes_change)

    def on_sound_modes_change(self, sound_modes):
        self.translation = sound_modes
        if self.isset():
            self.on_change(self.get()) # cause listeners to update from self.translation
        
    def matches(self, data): return super().matches(data) and data[len(self.function)+2] == "1"
    def serialize_val(self, val): return "%s1%s"%(super().serialize_val(val)[:2], val)
    def unserialize_val(self, data): return data[3:]


@Denon.add_feature
class TechnicalSoundMode(SelectFeature):
    category = Category.GENERAL
    function = "MS"
    translation = {"MOVIE":"Movie", "MUSIC":"Music", "GAME":"Game", "DIRECT": "Direct", "PURE DIRECT":"Pure Direct", "STEREO":"Stereo", "STANDARD": "Standard", "DOLBY DIGITAL":"Dolby Digital", "DTS SURROUND":"DTS Surround", "MCH STEREO":"Multi ch. Stereo", "ROCK ARENA":"Rock Arena", "JAZZ CLUB":"Jazz Club", "MONO MOVIE":"Mono Movie", "MATRIX":"Matrix", "VIDEO GAME":"Video Game", "VIRTUAL":"Virtual",
        "VIRTUAL:X":"DTS Virtual:X","NEURAL:X":"DTS Neural:X","DOLBY SURROUND":"Dolby Surround","M CH IN+DS":"Multi Channel In + Dolby S.", "M CH IN+NEURAL:X": "Multi Channel In + DTS Neural:X", "M CH IN+VIRTUAL:X":"Multi Channel In + DTS Virtual:X", "MULTI CH IN":"Multi Channel In", #undocumented
    }

    def __init__(self, *args, **xargs):
        super().__init__(*args, **xargs)
        if isinstance(self.target, ServerType): self.bind(on_change=self.update_sound_mode)

    def update_sound_mode(self, val):
        sound_mode = self.target.features.sound_mode
        if val in sound_mode.options: sound_mode.set(val)

    def matches(self, data): return super().matches(data) and not data.startswith("MSQUICK")
    def on_change(self, val):
        super().on_change(val)
        self.target.features["%s_volume"%SPEAKERS[0][1]].async_poll(force=True)
        self.target.features.sound_mode_setting.async_poll(force=True)


class _QuickSelect(SelectFeature):
    function="MSQUICK"
    translation = {str(n+1):str(n+1) for n in range(5)}

@Denon.add_feature
class QuickSelect(_QuickSelect):
    name = "Quick Select (load)"
    call="MSQUICK ?"
    def get(self): return "(None)" if super().get() == "0" else super().get()
    def matches(self, data): return super().matches(data) and not data.endswith("MEMORY")


@Denon.add_feature
class QuickSelectStore(features.ClientToServerFeatureMixin, _QuickSelect):
    name = "Quick Select (save)"
    
    # for server:
    def matches(self, data): return super().matches(data) and data.endswith("MEMORY")
    def serialize_val(self, value): return f"{value} MEMORY"
    def unserialize_val(self, data): return data.split(" ",1)[0]
    
    def on_change(self, val):
        super().on_change(val)
        self.target.features.quick_select.set(val)
        
    def resend(self):
        self.target.schedule(lambda quick_select: quick_select.resend(), requires=("quick_select",))


@Denon.add_feature
class HdmiMonitor(SelectFeature):
    name = "HDMI Monitor auto detection"
    category = Category.VIDEO
    function = "VSMONI"
    call = "VSMONI ?"
    translation = {"MONI1":"OUT-1", "MONI2":"OUT-2"}
    
@Denon.add_feature
class Asp(SelectFeature):
    name = "ASP mode"
    function = "VSASP"
    call = "VSASP ?"
    translation = {"NRM":"Normal", "FUL":"Full"}
    
class _Resolution(SelectFeature):
    category = Category.VIDEO
    translation = {"48P":"480p/576p", "10I":"1080i", "72P":"720p", "10P":"1080p", "10P24":"1080p:24Hz", "AUTO":"Auto"}

@Denon.add_feature
class Resolution(_Resolution):
    function = "VSSC"
    call = "VSSC ?"
    def matches(self, data): return super().matches(data) and not data.startswith("VSSCH")
    
@Denon.add_feature
class HdmiResolution(_Resolution):
    name = "HDMI Resolution"
    function = "VSSCH"
    call = "VSSCH ?"

@Denon.add_feature
class HdmiAudioOutput(SelectFeature):
    name = "HDMI Audio Output"
    category = Category.VIDEO
    function = "VSAUDIO "
    translation = {"AMP":"to Amp", "TV": "to TV"}
    
@Denon.add_feature
class VideoProcessingMode(SelectFeature):
    category = Category.VIDEO
    function = "VSVPM"
    call = "VSVPM ?"
    translation = {"AUTO":"Auto", "GAME":"Game", "MOVI": "Movie"}
    
@Denon.add_feature
class ToneControl(BoolFeature):
    category = Category.GENERAL
    function = "PSTONE CTRL "
    
@Denon.add_feature
class SurroundBackMode(SelectFeature):
    name = "Surround Back SP Mode"
    function = "PSSB:"
    call = "PSSB: ?"
    translation = {"MTRX ON": "Matrix", "PL2x CINEMA":"Cinema", "PL2x MUSIC": "Music", "ON":"On", "OFF":"Off"}
    
@Denon.add_feature
class CinemaEq(BoolFeature):
    name = "Cinema Eq."
    function = "PSCINEMA EQ."
    call = "PSCINEMA EQ. ?"

@Denon.add_feature
class Mode(SelectFeature):
    function = "PSMODE:"
    call = "PSMODE: ?"
    translation = {"MUSIC":"Music","CINEMA":"Cinema","GAME":"Game","PRO LOGIC":"Pro Logic"}
    
@Denon.add_feature
class FrontHeight(BoolFeature):
    function = "PSFH:"
    call = "PSFH: ?"

@Denon.add_feature
class Pl2hg(SelectFeature):
    name = "PL2z Height Gain"
    function = "PSPHG "
    translation = {"LOW":"Low","MID":"Medium","HI":"High"}
    
@Denon.add_feature
class SpeakerOutput(SelectFeature):
    function = "PSSP:"
    call = "PSSP: ?"
    translation = {"FH":"F. Height", "FW":"F. Wide", "SB":"S. Back"}
    
@Denon.add_feature
class MultEq(SelectFeature):
    name = "MultEQ XT mode"
    category = Category.AUDYSSEY
    function = "PSMULTEQ:"
    call = "PSMULTEQ: ?"
    translation = {"AUDYSSEY":"Audyssey", "BYP.LR":"L/R Bypass", "FLAT":"Flat", "MANUAL":"Manual", "OFF":"Off"}
    
@Denon.add_feature
class DynamicEq(BoolFeature):
    category = Category.AUDYSSEY
    function = "PSDYNEQ "
    
@Denon.add_feature
class ReferenceLevel(SelectFeature):
    category = Category.AUDYSSEY
    function = "PSREFLEV "
    translation = {"0":"0 dB","5":"5 dB","10":"10 dB","15":"15 dB"}
    
@Denon.add_feature
class DynamicVolume(SelectFeature):
    category = Category.AUDYSSEY
    function = "PSDYNVOL "
    options = ["Off","Light","Medium","Heavy"]
    translation = {"LIT":"Light","MED":"Medium","HEV":"Heavy", #undocumented
        "NGT":"Heavy", "EVE":"Medium", "DAY":"Light","OFF":"Off"}
    
@Denon.add_feature
class AudysseyDsx(SelectFeature):
    name = "Audyssey DSX"
    category = Category.AUDYSSEY
    function = "PSDSX "
    translation = {"ONH":"On (Height)", "ONW":"On (Wide)","OFF":"Off"}
    
@Denon.add_feature
class StageWidth(IntFeature): function = "PSSTW "

@Denon.add_feature
class StageHeight(IntFeature): function = "PSSTH "
    
@Denon.add_feature
class Bass(RelativeInt):
    category = Category.GENERAL
    function = "PSBAS "
    
@Denon.add_feature
class Treble(RelativeInt):
    category = Category.GENERAL
    function = "PSTRE "
    
@Denon.add_feature
class Drc(SelectFeature):
    function = "PSDRC "
    translation = {"AUTO":"Auto", "LOW":"Low", "MID":"Medium", "HI":"High", "OFF":"Off"}

@Denon.add_feature
class DynamicCompression(SelectFeature):
    function = "PSDCO "
    translation = {"LOW":"Low", "MID":"Medium", "HI":"High", "OFF":"Off"}

@Denon.add_feature
class Lfe(IntFeature):
    name = "LFE"
    category = Category.AUDIO
    function = "PSLFE "
    min=-10
    max=0
    def unserialize_val(self, val): return super().unserialize_val(val)*-1
    def serialize_val(self, val): return super().serialize_val(val*-1)

@Denon.add_feature
class EffectLevel(IntFeature): function = "PSEFF "
    
@Denon.add_feature
class Delay(IntFeature):
    category = Category.AUDIO
    max=999
    function = "PSDEL "
    
@Denon.add_feature
class Afd(BoolFeature):
    name = "AFDM"
    function = "PSAFD "
    
@Denon.add_feature
class Panorama(BoolFeature): function = "PSPAN "

@Denon.add_feature
class Dimension(IntFeature): function = "PSDIM "

@Denon.add_feature
class CenterWidth(IntFeature): function = "PSCEN "
    
@Denon.add_feature
class CenterImage(IntFeature): function = "PSCEI "
    
@Denon.add_feature
class Subwoofer(BoolFeature):
    category = Category.BASS
    function = "PSSWR "

class _SubwooferAdjustment: #undocumented
    category = Category.BASS
    #category = Category.AUDIO
    function = "PSSWL "
    name = "Subwoofer Adjustment"

@Denon.add_feature
class SubwooferAdjustmentActive(_SubwooferAdjustment, LooseBoolFeature): pass

@Denon.add_feature
class SubwooferAdjustment(_SubwooferAdjustment, LooseDecimalFeature): pass

class _DialogLevel: #undocumented
    category = Category.AUDIO
    function = "PSDIL "
    name = "Dialog Level"

@Denon.add_feature
class DialogLevelActive(_DialogLevel, LooseBoolFeature): pass

@Denon.add_feature
class DialogLevel(_DialogLevel, LooseDecimalFeature): pass

@Denon.add_feature
class RoomSize(SelectFeature):
    function = "PSRSZ "
    translation = {e:e for e in ["S","MS","M","ML","L"]}
    
@Denon.add_feature
class AudioDelay(IntFeature):
    category = Category.AUDIO
    max = 999
    function = "PSDELAY "

@Denon.add_feature
class Restorer(SelectFeature):
    name = "Audio Restorer"
    category = Category.AUDIO
    function = "PSRSTR "
    translation = {"OFF":"Off", "MODE1":"Mode 1", "MODE2":"Mode 2", "MODE3":"Mode 3"}
    
@Denon.add_feature
class FrontSpeaker(SelectFeature):
    function = "PSFRONT"
    translation = {" SPA":"A"," SPB":"B"," A+B":"A+B"}
    
@Denon.add_feature
class Crossover(SelectFeature): #undocumented
    name = "Crossover Speaker Select"
    category = Category.SPEAKERS
    function = "SSCFR "
    translation = {"ALL":"All","IDV":"Individual"}
    def matches(self, data): return super().matches(data) and "END" not in data

class _Crossover(SelectFeature): #undocumented
    category = Category.SPEAKERS
    call = "SSCFR ?"
    translation = {x:"%d Hz"%int(x)
        for x in ["040","060","080","090","100","110","120","150","200","250"]}

@Denon.add_feature
class CrossoverAll(_Crossover): #undocumented
    name = "Crossover (all)"
    function = "SSCFRALL "

for code, f_id, name in SPEAKER_PAIRS:
    @Denon.add_feature
    class CrossoverSpeaker(_Crossover): #undocumented
        name = f"Crossover ({name})"
        id = f"crossover_{f_id}"
        function = f"SSCFR{code} "

@Denon.add_feature
class SubwooferMode(SelectFeature): #undocumented
    category = Category.BASS
    function = "SSSWM "
    translation = {"L+M":"LFE + Main", "LFE":"LFE"}
    
@Denon.add_feature
class LfeLowpass(SelectFeature): #undocumented
    name = "LFE Lowpass Freq."
    category = Category.BASS
    function = "SSLFL "
    translation = {x:"%d Hz"%int(x) 
        for x in ["080","090","100","110","120","150","200","250"]}

@Denon.add_feature
class Display(SelectFeature):
    function = "DIM "
    translation = {"BRI":"Bright","DIM":"Dim","DAR":"Dark","OFF":"Off"}

@Denon.add_feature
class Idle(features.ServerToClientFeatureMixin, BoolFeature): #undocumented
    """
    Information on Audio Input Signal
    Value seems to indicate if amp is playing something via HDMI
    """
    category = Category.INPUT
    function = "SSINFAISSIG "
    translation = {"01": True, "02": False, "12": True} #01: analog, 02: PCM

    def matches(self, data): return super().matches(data) and isinstance(self.unserialize(data), bool)


@Denon.add_feature
class Bitrate(features.ServerToClientFeatureMixin, SelectFeature):
    category = Category.INPUT
    function = "SSINFAISFSV "
    translation = {"NON": "-"}
    dummy_value = "441"


@Denon.add_feature
class SampleRate(SelectFeature): #undocumented
    """ Information on Audio Input Signal Sample Rate """
    category = Category.INPUT
    function = "SSINFAISFV "


@Denon.add_feature
class AutoStandby(SelectFeature):
    category = Category.ECO
    function = "STBY"
    translation = {"OFF":"Off","15M":"15 min","30M":"30 min","60M":"60 min"}


@Denon.add_feature
class AmpAssign(SelectFeature): #undocumented
    category = Category.SPEAKERS
    function = "SSPAAMOD "
    call = "SSPAA ?"
    translation = {"FRB": "Front B", "BIA": "Bi-Amping", "NOR": "Surround Back", "FRH": "Front Height", "TFR": "Top Front", "TPM": "Top Middle", "FRD": "Front Dolby", "SUD": "Surround Dolby", **{"ZO%s"%zone:"Zone %s"%zone for zone in ZONES}}


@Denon.add_feature
class VolumeOsd(SelectFeature): #undocumented
    category = Category.VIDEO
    function = "SSOSDVOL "
    translation = {"TOP":"Top","BOT":"Bottom","OFF":"Off"}


@Denon.add_feature
class InfoOsd(BoolFeature): #undocumented
    category = Category.VIDEO
    function = "SSOSDTXT "


@Denon.add_feature
class HdmiRcSelect(SelectFeature): #undocumented
    function = "SSHOSRSS "
    call = "SSHOS ?"
    translation = {"POS":"Power On + Source", "SSO":"Only Source"}


@Denon.add_feature
class HdmiControl(BoolFeature): #undocumented
    function = "SSHOSCON "
    call = "SSHOS ?"


@Denon.add_feature
class Language(SelectFeature): #undocumented
    function = "SSLAN "
    translation = {"DEU":"German", "ENG":"English", "ESP":"Spanish", "POL":"Polish", "RUS": "Russian",
        "FRA":"French", "ITA":"Italian", "NER":"Dutch", "SVE":"Swedish"}


@Denon.add_feature
class EcoMode(SelectFeature): #undocumented
    category = Category.ECO
    function = "ECO"
    translation = {"AUTO":"Auto","ON":"On","OFF":"Off"}


for code, f_id, name in SOURCES:
    @Denon.add_feature
    class InputVisibility(BoolFeature): #undocumented
        name = f"Enable {name} Input"
        id = f"enable_{f_id}"
        category = Category.INPUT
        call = "SSSOD ?"
        function = f"SSSOD{code} "
        translation = {"USE":True, "DEL":False}


for code, f_id, name in SOURCES:
    @Denon.add_feature
    class SourceVolumeLevel(RelativeInt): #undocumented
        name = f"{name} Volume Level"
        id = f"{f_id}_volume_level"
        category = Category.INPUT
        min = -12
        max = 12
        call = "SSSLV ?"
        function = f"SSSLV{code} "
        def remote_set(self, *args, **xargs):
            super().remote_set(*args, **xargs)
            self.async_poll(force=True) #Denon workaround: missing echo


@Denon.add_feature
class SpeakerDistanceStep(SelectFeature): #undocumented
    category = Category.SPEAKERS
    call = "SSSDE ?"
    function = "SSSDESTP "
    translation = {"01M": "0.1m", "02M": "0.01m", "01F": "1ft", "02F": "0.1ft"}


for code, f_id, name in SPEAKERS:
    @Denon.add_feature
    class SpeakerDistance(IntFeature): #undocumented
        name = f"{name} Distance"
        id = f"{f_id}_distance"
        category = Category.SPEAKERS
        min = 0
        max = 1800
        call = "SSSDE ?"
        function = f"SSSDE{code} "


@Denon.add_feature
class MenuVisibility(BoolFeature): #undocumented
    category = Category.VIDEO
    function = "MNMEN "


@Denon.add_feature
class SerialNumber(SelectFeature):
    call = "VIALL?"
    function = "VIALLS/N."


@Denon.add_feature
class VolumeScale(SelectFeature):
    category = Category.VOLUME
    function = "SSVCTZMADIS "
    call = "SSVCTZMA ?"
    translation = {"REL":"-79-18 dB", "ABS":"0-98"}


@Denon.add_feature
class PowerOnLevel(LooseIntFeature):
    category = Category.VOLUME
    id = "power_on_level_numeric"
    function = "SSVCTZMAPON "
    call = "SSVCTZMA ?"


@Denon.add_feature
class PowerOnLevel(SelectFeature):
    category = Category.VOLUME
    function = "SSVCTZMAPON "
    call = "SSVCTZMA ?"
    translation = {"MUT":"Muted", "LAS":"Unchanged"}
    def on_change(self, val):
        super().on_change(val)
        if not self.target.features.power_on_level_numeric.isset():
            self.target.features.power_on_level_numeric.set(0)


@Denon.add_feature
class MuteMode(SelectFeature):
    category = Category.VOLUME
    function = "SSVCTZMAMLV "
    call = "SSVCTZMA ?"
    translation = {"MUT":"Full", "040":"-40 dB", "060":"-20 dB"}


for source_code, source_id, source_name in SOURCES:
    for input_code, input_value_code, input_id, input_name in INPUTS:
        @Denon.add_feature
        class SourceInputAssign(SelectFeature):
            name = f"{source_name} {input_name} Input"
            id = f"input_{source_id}_{input_id}"
            category = Category.INPUT
            function = f"SS{input_code}{source_code} "
            call = f"SS{input_code} ?"
            translation = {"OFF":"None", "FRO":"Front",
                **{f"{input_value_code}{i}":f"{input_name} {i}" for i in range(7)}}


class Equalizer: category = Category.EQUALIZER

@Denon.add_feature
class EqualizerActive(Equalizer, BoolFeature): function = "PSGEQ "

@Denon.add_feature
class EqualizerChannels(Equalizer, SelectFeature):
    function = "SSGEQSPS "
    translation = {cat_code: cat_name for cat_code, cat_id, cat_name, l in EQ_OPTIONS}

for cat_code, cat_id, cat_name, l in EQ_OPTIONS:
    for code, sp_id, name in l:

        @Denon.add_feature
        class SpeakerEq(Equalizer, DenonFeature, features.Feature): #undocumented
            name = f"Eq {name}"
            type = dict
            id = f"eq_{cat_id}_{sp_id}"
            function = f"SSAEQ{cat_code}{code} "
            call = f"SSAEQ{cat_code} ?"
            dummy_value = {i:0 for i in range(9)}
            
            def serialize_val(self, d): return ":".join(["%d"%(v*10+500) for v in d.values()])

            def unserialize_val(self, data):
                return {i: Decimal(v)/10-50 for i, v in enumerate(data.split(":"))}

            def set_value(self, key, val):
                self.set({**self.get(), key:DecimalFeature._roundVolume(val)})

            def remote_set_value(self, key, val, *args, **xargs):
                self.remote_set({**self.get(), key:DecimalFeature._roundVolume(val)}, *args, **xargs)


        for bound, bound_name in enumerate(EQ_BOUNDS):

            @Denon.add_feature
            class Bound(Equalizer, features.OfflineFeatureMixin, DecimalFeature): #undocumented
                name = f"Eq {name} {bound_name}"
                id = f"eq_{cat_id}_{sp_id}_bound{bound}"
                min = -20
                max = +6
                
                def __init__(self, *args, cat_id=cat_id, sp_id=sp_id, **xargs):
                    super().__init__(*args, **xargs)
                    self._channels = self.target.features.equalizer_channels
                    self._channels.bind(on_change = self.update)
                    self._speaker_eq = self.target.features[f"eq_{cat_id}_{sp_id}"]
                    self._speaker_eq.bind(on_change = self.update)
                
                def update(self, val, cat_name=cat_name, bound=bound):
                    if isinstance(self.target, ServerType): return
                    isset = self._channels.isset() and self._channels.get() == cat_name \
                        and self._speaker_eq.isset()
                    super().set(self._speaker_eq.get()[bound]) if isset else self.unset()
                
                def set(self, value, bound=bound): self._speaker_eq.set_value(bound, self.type(value))

                def remote_set(self, value, *args, bound=bound, **xargs):
                    self._speaker_eq.remote_set_value(bound, self.type(value))
                
                def async_poll(self, *args, **xargs):
                    if not self._channels.isset(): self._channels.async_poll(*args, **xargs)
                    if not self._speaker_eq.isset(): self._speaker_eq.async_poll(*args, **xargs)


@Denon.add_feature
class EnergyUse(IntFeature): #undocumented
    category = Category.ECO
    function = "SSECOSTS "


# TODO: implement PV

for zone in ZONES:
    
    class Zone:
        category = getattr(Category, f"ZONE_{zone}")
    
    @Denon.add_feature
    class ZVolume(Zone, Volume):
        name = "Zone %s Volume"%zone
        id = "zone%s_volume"%zone
        function = "Z%s"%zone
        
    @Denon.add_feature
    class ZPower(Zone, BoolFeature):
        name = "Zone %s Power"%zone
        id = "zone%s_power"%zone
        function = "Z%s"%zone
        def matches(self, data): return super().matches(data) and data[len(self.function):] in self.translation
    
    @Denon.add_feature
    class ZSource(Zone, Source):
        name = "Zone %s Source"%zone
        id = "zone%s_source"%zone
        function = "Z%s"%zone
        translation = {**Source.translation, "SOURCE": "Main Zone"}
        _from_mainzone = False
        
        def __init__(self, *args, **xargs):
            super().__init__(*args, **xargs)
            self.target.features.source.bind(lambda *_:self._resolve_main_zone_source())

        def matches(self, data): return super().matches(data) and data[len(self.function):] in self.translation

        def _resolve_main_zone_source(self):
            self.target.schedule(lambda source: self._from_mainzone and Source.set(self, source.get()),
                requires=("source",))

        def set(self, data):
            self._from_mainzone = data == "Main Zone"
            if self._from_mainzone: self._resolve_main_zone_source()
            else: return super().set(data)
        
        def unset(self):
            super().unset()
            self._from_mainzone = False
    
    @Denon.add_feature
    class ZMuted(Zone, Muted):
        name = "Zone %s Muted"%zone
        id = "zone%s_muted"%zone
        function = "Z%sMU"%zone
    
    @Denon.add_feature
    class ChannelSetting(Zone, SelectFeature):
        id = "zone%s_channel_setting"%zone
        function = "Z%sCS"%zone
        translation = {"MONO":"Mono","ST":"Stereo"}
    
    @Denon.add_feature
    class ZFrontLeftVolume(Zone, RelativeDecimal):
        id = "zone%s_front_left_volume"%zone
        name = "Front Left Volume"
        function = "Z%sFL "%zone
        call = "Z%sCV?"%zone
        
    @Denon.add_feature
    class ZFrontRightVolume(Zone, RelativeDecimal):
        id = "zone%s_front_right_volume"%zone
        name = "Front Right Volume"
        function = "Z%sFR "%zone
        call = "Z%sCV?"%zone
        
    @Denon.add_feature
    class Hpf(Zone, BoolFeature):
        id = "zone%s_hpf"%zone
        name = "HPF"
        function = "Z%sHPF"%zone
    
    @Denon.add_feature
    class ZBass(Zone, RelativeInt):
        name = "Zone %s Bass"%zone
        id = "zone%s_bass"%zone
        function = "Z%sPSBAS "%zone
        
    @Denon.add_feature
    class ZTreble(Zone, RelativeInt):
        name = "Zone %s Treble"%zone
        id = "zone%s_treble"%zone
        function = "Z%sPSTRE "%zone
        
    @Denon.add_feature
    class Mdmi(Zone, SelectFeature):
        name = "MDMI Out"
        id = "zone%s_mdmi"%zone
        function = "Z%sHDA "%zone
        call = "Z%sHDA?"%zone
        translation = {"THR":"THR", "PCM":"PCM"}
        
    @Denon.add_feature
    class ZSleep(Zone, Sleep):
        name = "Zone %s Sleep (min.)"%zone
        id = "zone%s_sleep"%zone
        function = "Z%sSLP"%zone
        
    @Denon.add_feature
    class AutoStandby(Zone, SelectFeature):
        name = "Zone %s Auto Standby"%zone
        id = "zone%s_auto_standby"%zone
        function = "Z%sSTBY"%zone
        translation = {"2H":"2 hours","4H":"4 hours","8H":"8 hours","OFF":"Off"}

