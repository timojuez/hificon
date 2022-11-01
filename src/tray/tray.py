import sys, math, pkgutil, os, tempfile, argparse, traceback
from threading import Thread
from contextlib import AbstractContextManager, ExitStack
from decimal import Decimal
from .. import Target
from ..core.util import Bindable
from . import gui
from .key_binding import KeyBinding
from .setup import Setup
from .common import gtk, config, resolve_feature_id, APP_NAME, AbstractApp
from .setup_wizard import SetupWizard
from .power_control import PowerControlMixin
from .notifications import NotificationMixin


class Icon(Bindable):
    """ Functions regarding loading images from src/share """
    
    def __init__(self, target):
        self.target = target
        self._icon_name = None
        self.target.bind(
            on_connect=self.update_icon,
            on_disconnected=self.set_icon,
            on_feature_change=self.on_feature_change)

    def bind(self, *args, **xargs):
        super().bind(*args, **xargs)
        self.set_icon()
        self.update_icon()

    def on_feature_change(self, f_id, value, *args): # bound to target
        if f_id in (config.tray_feature, config.muted, config.power): self.update_icon()

    def update_icon(self):
        self.target.schedule(self._update_icon, requires=(config.muted, config.tray_feature, config.power))

    def _update_icon(self):
        f = self.target.features[config.tray_feature]
        if not self.target.features[config.power].get(): self.set_icon("power")
        elif self.target.features[config.muted].get() or f.get() == f.min:
            self.set_icon("audio-volume-muted")
        else:
            f_val = f.get()
            if not (f.min <= f_val <= f.max):
                return sys.stderr.write(
                    f"[{self.__class__.__name__}] WARNING: Value out of bounds: {f_val} for {f.id}.\n")
            icons = ["audio-volume-low","audio-volume-medium","audio-volume-high"]
            icon_idx = math.ceil((f_val-f.min)/(f.max-f.min)*len(icons))-1
            self.set_icon(icons[icon_idx])

    def set_icon(self, name="disconnected"):
        if self._icon_name == name: return
        self._icon_name = name
        image_data = pkgutil.get_data(__name__, f"../share/icons/scalable/{name}.svg")
        with open(self._path, "wb") as fp: fp.write(image_data)
        self.on_change(self._path, name)

    def on_change(self, path, name): pass
    
    def __enter__(self):
        self._path = tempfile.mktemp()
        return self
    
    def __exit__(self, *args):
        try: os.remove(self._path)
        except FileNotFoundError: pass


class TrayMixin(gui.Tray):
    """ Tray Icon """

    def __init__(self, *args, icon, **xargs):
        super().__init__(*args,**xargs)
        self.target.preload_features.update((config.tray_feature, config.muted))
        icon.bind(on_change = self.on_icon_change)
        self.icon = icon
        self.show()

    def on_icon_change(self, path, name):
        self.scale_popup.set_image(path)
        self.set_icon(path, name)

    def _save_set_feature_to_relative_value(self, f_id, add):
        f = self.target.features.get(f_id)
        if not f or not f.isset(): return
        try:
            value = f.get()+add
            snapped_value = min(max(f.min, value), f.max)
            f.remote_set(snapped_value)
        except ConnectionError: pass

    def on_scroll_up(self, steps):
        self._save_set_feature_to_relative_value(
            config.tray_feature, steps*Decimal(config["tray"]["scroll_delta"]))

    def on_scroll_down(self, steps):
        self._save_set_feature_to_relative_value(
            config.tray_feature, steps*-1*Decimal(config["tray"]["scroll_delta"]))


class App(AbstractApp, NotificationMixin, PowerControlMixin, KeyBinding, TrayMixin, AbstractContextManager):
    pass


class AppManager:

    def __init__(self, verbose):
        self.main_app = None
        self._exit_stack = ExitStack()
        self.verbose = verbose+1

    def mainloop(self):
        with self._exit_stack: gui.GUI_Backend.mainloop()

    @gtk
    def run_app(self, uri=None, setup=False, callback=None):
        self._exit_stack.close()
        if setup or not config["target"]["setup_mode"]:
            return SetupWizard(self, first_run=True).show()
        target = Target(uri, connect=False, verbose=self.verbose)
        icon = self._exit_stack.enter_context(Icon(target))
        self.main_app = self._exit_stack.enter_context(App(self, target, icon=icon, verbose=self.verbose))
        self._exit_stack.enter_context(target)
        if callback: callback()

    @gtk
    def main_quit(self):
        gui.GUI_Backend.exit()


def main():
    parser = argparse.ArgumentParser(description=APP_NAME)
    parser.add_argument('--setup', default=False, action="store_true", help='Run initial setup')
    parser.add_argument('-t', '--target', metavar="URI", type=str, default=None, help='Target URI')
    parser.add_argument('--verbose', '-v', action='count', default=0, help='Verbose mode')
    args = parser.parse_args()

    am = AppManager(verbose=args.verbose)
    Thread(target=lambda: am.run_app(args.target, args.setup), name="mainapp", daemon=True).start()
    am.mainloop()

