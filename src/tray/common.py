import gi, pkgutil
gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk
from ..core.config import YamlConfig
from .. import NAME


APP_NAME = f"{NAME} Tray Control"


class Singleton(type):
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


def gtk(func):
    return lambda *args,**xargs: GLib.idle_add(lambda:[False, func(*args,**xargs)][0])


class AbstractApp:

    def __init__(self, app_manager, *args, **xargs):
        self.app_manager = app_manager
        super().__init__(*args, **xargs)


class GladeGtk:
    GLADE = ""
    
    def __init__(self, *args, **xargs):
        super().__init__(*args, **xargs)
        self.builder = Gtk.Builder()
        self.builder.add_from_string(pkgutil.get_data(__name__, self.GLADE).decode())
        self.builder.connect_signals(self)

    @gtk
    def show(self): self.window.present()

    @gtk
    def hide(self): self.window.hide()


class TrayConfig(YamlConfig):

    def __init__(self): super().__init__("tray.yml")
    volume = property(lambda self: self["target"]["features"]["volume_id"])
    muted = property(lambda self: self["target"]["features"]["muted_id"])
    power = property(lambda self: self["target"]["features"]["power_id"])
    source = property(lambda self: self["target"]["features"]["source_id"])
    tray_feature = property(lambda self: resolve_feature_id(self["tray"]["scroll_feature"]))
    gesture_feature = property(lambda self: resolve_feature_id(self["hotkeys"]["mouse_feature"]))
    hotkeys_feature = property(lambda self: resolve_feature_id(self["hotkeys"]["hotkeys_feature"]))


config = TrayConfig()


def resolve_feature_id(f_id):
    return config["target"]["features"].get(f_id[1:]) if f_id.startswith("@") else f_id

def id_to_feature(target, f_id):
    if target: return target.features.get(f_id)

def id_to_string(target, f_id):
    f_id = resolve_feature_id(f_id)
    f = id_to_feature(target, f_id)
    return f"{f.name} ({f.category})" if f else f"{f_id} (Unavailable)"

