import gi, pkgutil
gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk, GObject
from ..core.transmission import features
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


class _FeatureCombobox:

    def __init__(self, target, combobox):
        self.c = combobox
        self.target = target
        self.store = Gtk.TreeStore(str, GObject.TYPE_PYOBJECT)
        self.fill()
        renderer_text = Gtk.CellRendererText()
        self.c.clear()
        self.c.pack_start(renderer_text, expand=True)
        self.c.add_attribute(renderer_text, "text", column=0)

    #_active_value stores the value if the selection is not in the model
    _active_values = {}
    def _active_value_get(self): return self._active_values.get(self.c)
    def _active_value_set(self, val): self._active_values[self.c] = val
    _active_value = property(_active_value_get, _active_value_set)

    def fill(self):
        active = self.get_active()
        self.store.clear()
        self._fill()
        self.c.set_model(self.store)
        self.set_active(active)

    def _fill(self): raise NotImplementedError()

    def get_active(self):
        it = self.c.get_active_iter()
        return self.c.get_model().get_value(it, 1) if it else self._active_value

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

    def _fill(self):
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
        if self._feature:
            self._feature.bind(on_change=lambda *_: gtk(self.fill)())
            self.target.preload_features.add(f_id)
            try: self._feature.async_poll()
            except ConnectionError: pass

    def _fill(self):
        if not self._feature: return
        for val in self._feature.options: self.store.append(None, [str(val), val])

