import gi, pkgutil
gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk, GObject
from contextlib import AbstractContextManager
from ..core.transmission import features
from ..core.config import YamlConfig
from ..core.util.autostart import Autostart
from ..core.target_controller import TargetController
from .. import Target
from .. import NAME


APP_NAME = f"{NAME} Tray Control"
autostart = Autostart(__package__, __package__, terminal=False)


class AbstractApp:

    def __init__(self, app_manager, *args, **xargs):
        self.app_manager = app_manager
        super().__init__(*args, **xargs)


class _TargetApp(TargetController, AbstractContextManager):

    def __init__(self, uri, *args, **xargs):
        self.target = Target(uri, connect=False, verbose=xargs.get("verbose", 0))
        super().__init__(self.target, *args, **xargs)

    def __enter__(self):
        self.target.__enter__()
        return super().__enter__()

    def __exit__(self, *args, **xargs):
        try: super().__exit__(*args, **xargs)
        finally: self.target.__exit__(*args, **xargs)

    def main_quit(self):
        """ called by SystemEvents """
        self.app_manager.main_quit()


class TargetApp(AbstractApp, _TargetApp):
    """ App that has the attribute self.target """
    pass


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
    idle = property(lambda self: self["target"]["features"]["idle_id"])
    tray_feature = property(lambda self: resolve_feature_id(self["tray"]["scroll_feature"]))
    gesture_feature = property(lambda self: resolve_feature_id(self["hotkeys"]["mouse_feature"]))
    hotkeys_feature = property(lambda self: resolve_feature_id(self["hotkeys"]["hotkeys_feature"]))


config = TrayConfig()


def resolve_feature_id(f_id):
    return config["target"]["features"].get(f_id[1:]) if f_id and f_id.startswith("@") else f_id

def id_to_feature(target, f_id):
    if target: return target.features.get(f_id)

def id_to_string(target, f_id):
    f_id = resolve_feature_id(f_id)
    f = id_to_feature(target, f_id)
    return f"{f.name} ({f.category})" if f else f"{f_id} (Unavailable)"


class _FeatureCombobox:

    def __init__(self, target, combobox, items=None):
        """ items: list [(name string, value any)]. Additional items that appear in the combobox """
        self.c = combobox
        self.target = target
        self._custom_items = items or []
        self.store = Gtk.TreeStore(str, GObject.TYPE_PYOBJECT, bool)
        self.fill()
        renderer_text = Gtk.CellRendererText()
        self.c.clear()
        self.c.pack_start(renderer_text, expand=True)
        self.c.add_attribute(renderer_text, "text", column=0)
        self.c.add_attribute(renderer_text, "sensitive", column=2)

    #_active_value stores the value if the selection is not in the model
    _active_values = {}
    def _active_value_get(self): return self._active_values.get(self.c)
    def _active_value_set(self, val): self._active_values[self.c] = val
    _active_value = property(_active_value_get, _active_value_set)

    def fill(self):
        active = self.get_active()
        self.store.clear()
        for text, value in self._custom_items:
            self.store.append(None, [text, value, True])
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

    def __init__(self, target, *args, allow_type=features.Feature, **xargs):
        self._allow_type = allow_type
        super().__init__(target, *args, **xargs)

    def _fill(self):
        if self.target:
            features_ = [f for f in self.target.features.values() if isinstance(f, self._allow_type)]
            categories = {f.category:0 for f in features_}
            category = {c:self.store.append(None, [c, -1, False]) for c in categories}
            for f in features_: self.store.append(category[f.category], [f.name, f.id, True])


class FeatureValueCombobox(_FeatureCombobox):

    def __init__(self, target, c, f_id, **xargs):
        self._feature = target.features.get(f_id) if target else None
        super().__init__(target, c, **xargs)
        if self._feature:
            self._feature.bind(on_change=lambda *_: gtk(self.fill)())
            self.target.preload_features.add(f_id)
            if not self._feature.isset():
                try: self._feature.async_poll()
                except ConnectionError: pass

    def _fill(self):
        if not self._feature: return
        for val in self._feature.options: self.store.append(None, [str(val), val, True])

