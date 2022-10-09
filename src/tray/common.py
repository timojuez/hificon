import gi, pkgutil
gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk
from ..core.config import YamlConfig


class Singleton(type):
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


def gtk(func):
    return lambda *args,**xargs: GLib.idle_add(lambda:[False, func(*args,**xargs)][0])


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


config = TrayConfig()

