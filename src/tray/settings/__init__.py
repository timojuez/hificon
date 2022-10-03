import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk
from ..common import GladeGtk, gtk
from .popup_menu_settings import PopupMenuSettings


class SettingsBase(GladeGtk):
    GLADE = "../share/settings.glade"

    def __init__(self, app_manager, target, config, *args, **xargs):
        super().__init__(*args, **xargs)
        self.app_manager = app_manager
        self.target = target
        self.window = self.builder.get_object("window")
        self.config = config
        item_poweroffsd = self.builder.get_object("poweroff")
        item_poweroffsd.set_active(self.config["control_power_off"])
        item_poweroffsd.connect("toggled", lambda *args:
            self.config.__setitem__("control_power_off",item_poweroffsd.get_active()))
        item_hotkeys = self.builder.get_object("hotkeys")
        item_hotkeys.set_active(self.config["volume_hotkeys"])
        item_hotkeys.connect("toggled", lambda *args:
            self.set_keyboard_media_keys(item_hotkeys.get_active()))

    def set_keyboard_media_keys(self, active):
        self.config.__setitem__("volume_hotkeys", active)

    def set_mouse_key(self, key):
        pass

    def on_close_click(self, *args, **xargs):
        if self._first_run: Gtk.main_quit()
        else: self.hide()
        return True

    def on_first_run(self):
        self._first_run = True

class Settings(PopupMenuSettings, SettingsBase): pass

