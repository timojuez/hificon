import sys, math, pkgutil, os, tempfile, argparse
from threading import Thread, Timer, Lock
from .. import Target
from .. import NAME
from ..core import features
from ..core.util import Bindable
from ..core.config import config, ConfigDict
from ..core.target_controller import TargetController
from . import gui
from .key_binding import KeyBinding
from .setup import Setup


class FeatureNotification:

    def __init__(self, feature, *args, **xargs):
        super().__init__(*args, **xargs)
        self.f = feature
        self.target = feature.target


class TextNotification(FeatureNotification, gui.Notification):
    
    def __init__(self, *args, **xargs):
        super().__init__(*args, **xargs)
        self.set_urgency(2)
        self.set_timeout(config.getint("Tray","notification_timeout"))
        super().update("Connecting ...", self.target.uri)
        self.target.preload_features.add("name")
    
    def update(self): self.target.schedule(self._update, requires=("name",))
    
    def _update(self):
        if not self.f.isset(): return
        val = {True:"On",False:"Off"}.get(self.f.get(), self.f.get())
        super().update(f"{self.f.name}: {val}", self.target.name)

    def show(self): self.target.schedule(super(TextNotification, self).show, requires=("name",))


class NumericNotification(FeatureNotification):
    
    def __init__(self, *args, **xargs):
        super().__init__(*args, **xargs)
        self._n = gui.GaugeNotification()
        self._n.set_timeout(config.getint("Tray","notification_timeout"))

    def update(self): pass

    def show(self):
        if gui.ScalePopup()._current_feature == self.f and gui.ScalePopup().visible: return
        self._n.update(
            title=self.f.name,
            message=str(self.f),
            value=self.f.get() if self.f.isset() else self.f.min,
            min=self.f.min,
            max=self.f.max)
        self._n.show()

    def hide(self): self._n.hide()
        

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
        if f_id in (config.volume, config.muted, config.power): self.update_icon()

    def update_icon(self):
        self.target.schedule(self._update_icon, requires=(config.muted, config.volume, config.power))

    def _update_icon(self):
        volume = self.target.features[config.volume]
        if not self.target.features[config.power].get(): self.set_icon("power")
        elif self.target.features[config.muted].get() or volume.get() == volume.min:
            self.set_icon("audio-volume-muted")
        else:
            icons = ["audio-volume-low","audio-volume-medium","audio-volume-high"]
            icon_idx = math.ceil(volume.get()/volume.max*len(icons))-1
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


class NotificationMixin(object):
    """ Does the graphical notifications """

    def __init__(self,*args,**xargs):
        super().__init__(*args,**xargs)
        notification_blacklist = config.getlist("Tray","notification_blacklist")
        n_features = [f for f in self.target.features.values()
            if f.id not in notification_blacklist]
        self._notifications = {f.id: n for f in n_features for n in [self.create_notification(f)] if n}
        self.target.preload_features.add(config.volume)
        self.target.bind(on_feature_change = self.show_notification_on_feature_change)
    
    def create_notification(self, f):
        if isinstance(f, features.NumericFeature): return NumericNotification(f)
        if isinstance(f, features.SelectFeature): return TextNotification(f)

    def show_notification(self, f_id): f_id in self._notifications and self._notifications[f_id].show()
    
    def on_mouse_down(self,*args,**xargs):
        self.show_notification(config.volume)
        super().on_mouse_down(*args,**xargs)

    def on_volume_key_press(self,*args,**xargs):
        self.show_notification(config.volume)
        super().on_volume_key_press(*args,**xargs)

    def show_notification_on_feature_change(self, f_id, value): # bound to target
        if f_id in self._notifications: self._notifications[f_id].update()
        if self.target.features[f_id]._prev_val is not None: self.show_notification(f_id)

    def on_scroll_up(self, *args, **xargs):
        self.show_notification(config.volume)
        super().on_scroll_up(*args,**xargs)
        
    def on_scroll_down(self, *args, **xargs):
        self.show_notification(config.volume)
        super().on_scroll_down(*args,**xargs)


class TrayMixin(gui.Tray):
    """ Tray Icon """

    def __init__(self, *args, icon, **xargs):
        self.config = ConfigDict("tray.json")
        super().__init__(*args,**xargs)
        self.target.preload_features.update((config.volume,config.muted))
        self.scroll_delta = config.getdecimal("Tray","tray_scroll_delta")
        icon.bind(on_change = self.on_icon_change)
        self.show()

    def on_icon_change(self, path, name):
        gui.ScalePopup(self.target).set_image(path)
        self.set_icon(path, name)
    
    def on_scroll_up(self, steps):
        volume = self.target.features[config.volume]
        try:
            if volume.isset(): volume.remote_set(volume.get()+self.scroll_delta*steps)
        except ConnectionError: pass

    def on_scroll_down(self, steps):
        volume = self.target.features[config.volume]
        try:
            if volume.isset(): volume.remote_set(volume.get()-self.scroll_delta*steps)
        except ConnectionError: pass


class AutoPower(TargetController):
    """ Power on when playing starts and show a notification warning to poweroff when idling """
    notification_timeout = 10
    _button_clicked = False
    _playing_lock = Lock
    _playing = False
    _idle_timer_lock = Lock
    _idle_timer = None

    def __init__(self, *args, **xargs):
        super().__init__(*args, **xargs)
        self._playing_lock = self._playing_lock()
        self._idle_timer_lock = self._idle_timer_lock()
        self.target.preload_features.update((config.source, config.power))
        self.target.preload_features.add("name")
        self.target.bind(
            on_feature_change = self.on_target_feature_change,
            on_disconnected = self.close_popup)
        self.target.features.is_playing.bind(self.on_target_playing)
        self._n = gui.Notification()
        buttons = [("Cancel", lambda:None), ("Snooze", self.snooze_notification), ("OK", self.poweroff)]
        for name, func in buttons:
            self._n.add_action(name, name,
                lambda *args,func=func,**xargs: [func(), setattr(self, '_button_clicked', True)])
        self._n.connect("closed", self.on_popup_closed)
        self._n.set_timeout(self.notification_timeout*1000)

    def on_target_playing(self, playing):
        if playing: self.on_unidle()
        else: self.on_idle()

    def on_start_playing(self):
        """ start playing locally, e.g. via pulse """
        super().on_start_playing()
        self.on_unidle()

    def on_stop_playing(self):
        """ stop playing locally """
        super().on_stop_playing()
        # execute on_idle() if target is not playing
        try: target_playing = self.target.features.is_playing.isset() and self.target.is_playing
        except ConnectionError: target_playing = False
        if not target_playing: self.on_idle()
        if not self.target.features.is_playing.isset():
            try: self.target.features.is_playing.async_poll()
            except ConnectionError: pass

    def on_idle(self):
        with self._playing_lock:
            self._playing = False
            self.start_idle_timer()

    def on_unidle(self):
        """ when starting to play something locally or on amp """
        with self._playing_lock:
            self._playing = True
            self.stop_idle_timer()
        self.poweron()

    def start_idle_timer(self):
        with self._idle_timer_lock:
            if self._playing or self._idle_timer and self._idle_timer.is_alive(): return
            try: timeout = config.getfloat("Amp","poweroff_after")*60
            except ValueError: return
            if not timeout: return
            self._idle_timer = Timer(timeout, self.on_idle_timeout)
            self._idle_timer.start()

    def stop_idle_timer(self):
        with self._idle_timer_lock:
            if self._idle_timer: self._idle_timer.cancel()
        self.close_popup()

    def on_target_feature_change(self, f_id, value):
        if f_id == config.power:
            if value == True: # poweron event
                self.start_idle_timer()
            elif value == False: # poweroff event
                self.stop_idle_timer()

    def snooze_notification(self):
        self.start_idle_timer()

    def on_popup_closed(self, *args):
        if self._n.get_closed_reason() == 1: # timeout
            self.poweroff()
        elif self._n.get_closed_reason() == 2 and not self._button_clicked: # clicked outside buttons
            self.snooze_notification()
        self._button_clicked = False
    
    def on_idle_timeout(self):
        self.target.schedule(self._on_idle_timeout, requires=("name", config.power, config.source))

    def _on_idle_timeout(self):
        if self.config["auto_power_off"] and self.can_poweroff:
            self._n.update("Power off %s"%self.target.name)
            self._n.show()
        
    def close_popup(self):
        try: self._n.close()
        except: pass

    def poweron(self):
        """ poweron target """
        if self.config["auto_power_on"]:
            self.target.schedule(self._poweron, requires=(config.power, config.source))

    def _poweron(self):
        if self.target.features[config.power].get(): return
        if config["Amp"].get("source"):
            self.target.features[config.source].remote_set(config.getlist("Amp","source")[0])
        self.target.features[config.power].remote_set(True)

    can_poweroff = property(
        lambda self: self.target.features[config.power].get()
        and (not config["Amp"]["source"] or self.target.features[config.source].get() in config.getlist("Amp","source")))

    def poweroff(self):
        if not self.config["control_power_off"]: return
        self.target.schedule(lambda:self.can_poweroff and self.target.features[config.power].remote_set(False),
            requires=(config.power, config.source))

    def mainloop(self):
        Thread(name="TargetController", target=lambda:TargetController.mainloop(self), daemon=True).start()
        super().mainloop()

    def exit(self):
        gui.GUI_Backend.exit()


class Main(NotificationMixin, AutoPower, KeyBinding, TrayMixin, gui.GUI_Backend): pass


def main():
    parser = argparse.ArgumentParser(description='%s tray icon'%NAME)
    parser.add_argument('--setup', default=False, action="store_true", help='Run initial setup')
    parser.add_argument('-t', '--target', metavar="URI", type=str, default=None, help='Target URI')
    parser.add_argument('--verbose', '-v', action='count', default=0, help='Verbose mode')
    args = parser.parse_args()
    if not Setup.configured() or args.setup: Setup.setup()

    target = Target(args.target, connect=False, verbose=args.verbose+1)
    with Icon(target) as icon:
        app = Main(target, icon=icon, verbose=args.verbose+1)
        with target, app: app.mainloop()

