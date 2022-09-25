from ..common import GladeGtk, gtk
from .popup_menu_settings import PopupMenuSettings
from .target_setup import TargetSetup


class SettingsBase(GladeGtk):
    GLADE = "../share/settings.glade"

    def __init__(self, target, config, *args, **xargs):
        super().__init__(*args, **xargs)
        self.target = target
        self.window = self.builder.get_object("window")
        self.config = config
        item_poweroffsd = self.builder.get_object("poweroff")
        item_poweroffsd.set_active(self.config["control_power_off"])
        item_poweroffsd.connect("state-set", lambda *args:
            self.config.__setitem__("control_power_off",item_poweroffsd.get_active()))
        item_hotkeys = self.builder.get_object("hotkeys")
        item_hotkeys.set_active(self.config["volume_hotkeys"])
        item_hotkeys.connect("state-set", lambda *args:
            self.set_keyboard_media_keys(item_hotkeys.get_active()))

    def set_keyboard_media_keys(self, active):
        self.config.__setitem__("volume_hotkeys", active)

    def set_mouse_key(self, key):
        pass

    def on_close_click(self, *args, **xargs):
        self.hide()
        return True


class Settings(TargetSetup, PopupMenuSettings, SettingsBase): pass
