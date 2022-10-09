import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk
from ..common import GladeGtk, gtk, config
from .popup_menu_settings import PopupMenuSettings
from .target_setup import TargetSetup


class HotkeysMixin:

    def __init__(self, *args, **xargs):
        super().__init__(*args, **xargs)
        item_poweroffsd = self.builder.get_object("poweroff")
        item_poweroffsd.set_active(config["power_control"]["control_power_off"])
        item_poweroffsd.connect("state-set", lambda *args:
            [config["power_control"].__setitem__("control_power_off",item_poweroffsd.get_active()), config.save()])
        item_hotkeys = self.builder.get_object("hotkeys")
        item_hotkeys.set_active(config["hotkeys"]["volume_hotkeys"])
        item_hotkeys.connect("state-set", lambda *args:
            self.set_keyboard_media_keys(item_hotkeys.get_active()))

    def set_keyboard_media_keys(self, active):
        config["hotkeys"].__setitem__("volume_hotkeys", active)
        config.save()

    def set_mouse_key(self, key):
        pass


class SettingsBase(GladeGtk):
    GLADE = "../share/settings.glade"

    def __init__(self, app_manager, target, *args, first_run=False, **xargs):
        super().__init__(*args, **xargs)
        self._first_run = first_run
        self.app_manager = app_manager
        self.target = target
        self.window = self.builder.get_object("window")

    def on_close_click(self, *args, **xargs):
        if self._first_run: self.app_manager.main_quit()
        else: self.hide()
        return True


class Settings(HotkeysMixin, TargetSetup, PopupMenuSettings, SettingsBase): pass

