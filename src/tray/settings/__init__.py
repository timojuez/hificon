import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GObject
from ...core.transmission import features
from ...core.util.autostart import Autostart
from ...info import PKG_NAME
from ..common import GladeGtk, gtk, config, id_to_string
from ..common import __package__ as tray_package
from .feature_selector_view import FeatureSelectorView
from .target_setup import TargetSetup


class _FeatureCombobox:

    def __init__(self, target, combobox):
        self._active_value = None
        self.c = combobox
        self.target = target
        self.store = Gtk.TreeStore(str, GObject.TYPE_PYOBJECT)
        self.fill()
        self.c.set_model(self.store)
        renderer_text = Gtk.CellRendererText()
        self.c.pack_start(renderer_text, expand=True)
        self.c.add_attribute(renderer_text, "text", column=0)

    def get_active(self):
        it = self.c.get_active_iter()
        return self.store.get_value(it, 1) if it else self._active_value

    def set_active(self, value):
        def iterate(store, path, it):
            v = store.get_value(it, 1)
            if v == value:
                self.c.set_active_iter(it)
                self._active_value = value
        self._active_value = value
        self.c.set_active(-1)
        self.store.foreach(iterate)

    def connect(self, name, cb):
        decorated = lambda *args: cb(*tuple([self if arg == self.c else arg for arg in args]))
        return self.c.connect(name, decorated)

    def __getattr__(self, name): return getattr(self.c, name)


class FeatureSelectorCombobox(_FeatureCombobox):

    def __init__(self, *args, allow_type=features.Feature, default_value=None, **xargs):
        self._allow_type = allow_type
        self._default_value = default_value
        super().__init__(*args, **xargs)

    def fill(self):
        if self._default_value:
            self.store.append(
                None, ["Default – %s"%id_to_string(self.target, self._default_value), self._default_value])
        if self.target:
            features_ = [f for f in self.target.features.values() if isinstance(f, self._allow_type)]
            categories = {f.category:0 for f in features_}
            category = {c:self.store.append(None, [c, None]) for c in categories}
            for f in features_: self.store.append(category[f.category], [f.name, f.id])


class FeatureValueCombobox(_FeatureCombobox):

    def __init__(self, target, c, f_id, **xargs):
        self._feature = target.features.get(f_id) if target else None
        super().__init__(target, c, **xargs)
        if self._feature: self._feature.bind(on_change=lambda *_: self.fill())

    def fill(self):
        if not self._feature: return
        active = self.get_active()
        self.store.clear()
        for val in self._feature.options: self.store.append(None, [str(val), val])
        if active: self.set_active(active)


class PowerControlMixin:

    def __init__(self, *args, **xargs):
        super().__init__(*args, **xargs)
        item_poweroffsd = self.builder.get_object("poweroff")
        item_poweroffsd.connect("state-set", config.connect_to_object(("power_control", "control_power_off"),
            item_poweroffsd.get_active, item_poweroffsd.set_active))
        self.connect_adjustment_to_config("poweroff_delay", ("power_control", "poweroff_after"))
        self.connect_feature_selector_to_config("power_source_function", ("target", "features", "source_id"))
        self.connect_value_selector_to_config("source_value", ("target", "source"), config.source)


class TrayIconMixin:

    def __init__(self, *args, **xargs):
        super().__init__(*args, **xargs)
        self.connect_adjustment_to_config("scroll_delta", ("tray", "scroll_delta"))
        self.connect_feature_selector_to_config(
            combobox_id="tray_icon_function", config_property=("tray", "scroll_feature"),
            allow_type=features.NumericFeature, default_value="@volume_id",
            on_changed=lambda *_:self.app_manager.main_app.icon.update_icon())


class HotkeysMixin:

    def __init__(self, *args, **xargs):
        super().__init__(*args, **xargs)
        item_hotkeys = self.builder.get_object("hotkeys")
        item_hotkeys.connect("state-set", config.connect_to_object(("hotkeys", "volume_hotkeys"),
            item_hotkeys.get_active, item_hotkeys.set_active))
        self.connect_feature_selector_to_config(
            combobox_id="mouse_gesture_function", config_property=("hotkeys", "mouse_feature"),
            allow_type=features.NumericFeature, default_value="@volume_id")
        self.connect_feature_selector_to_config(
            combobox_id="keyboard_hotkeys_function", config_property=("hotkeys", "hotkeys_feature"),
            allow_type=features.NumericFeature, default_value="@volume_id")
        self.connect_adjustment_to_config("mouse_sensitivity", ("hotkeys", "mouse_sensitivity"))
        self.connect_adjustment_to_config("mouse_max_steps", ("hotkeys", "mouse_max_step"))
        self.connect_adjustment_to_config("mouse_delay", ("hotkeys", "interval"))
        self.connect_adjustment_to_config("hotkey_steps", ("hotkeys", "step"))

    def set_mouse_key(self, key):
        pass


class PopupMenuSettings:

    def __init__(self, *args, on_menu_settings_change=None, **xargs):
        super().__init__(*args, **xargs)
        fs = FeatureSelectorView(self.target, self.builder.get_object("popup_menu_settings"), "Context Menu")
        if on_menu_settings_change: fs.bind(on_change = on_menu_settings_change)
        fs.bind(on_change = config.connect_to_object(["tray", "menu_features"], fs.get_value, fs.set_value))


class GeneralMixin:

    def __init__(self, *args, **xargs):
        super().__init__(*args, **xargs)
        checkbox = self.builder.get_object("autostart_checkbox")
        autostart = Autostart(PKG_NAME, tray_package, terminal=False)
        checkbox.set_active(autostart.get_active())
        checkbox.connect("toggled", lambda *_: autostart.set_active(checkbox.get_active()))


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

    def connect_feature_selector_to_config(self, combobox_id, config_property, *args, on_changed=None, **xargs):
        fc = FeatureSelectorCombobox(self.target, self.builder.get_object(combobox_id), *args, **xargs)
        self._connect_combobox_to_config(config_property, fc, on_changed)

    def connect_value_selector_to_config(self, combobox_id, config_property, *args, on_changed=None, **xargs):
        fc = FeatureValueCombobox(self.target, self.builder.get_object(combobox_id), *args, **xargs)
        self._connect_combobox_to_config(config_property, fc, on_changed)

    def _connect_combobox_to_config(self, config_property, fc, on_changed=None):
        on_changed_ = config.connect_to_object(config_property, fc.get_active, fc.set_active)
        fc.connect("changed", on_changed_)
        if on_changed: fc.connect("changed", on_changed)

    def connect_adjustment_to_config(self, adjustment_id, config_property):
        ad = self.builder.get_object(adjustment_id)
        ad.connect("value-changed", config.connect_to_object(config_property, ad.get_value, ad.set_value))


class Settings(PowerControlMixin, TrayIconMixin, HotkeysMixin, TargetSetup, PopupMenuSettings,
    GeneralMixin, SettingsBase): pass

