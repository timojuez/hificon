import sys, math, pkgutil, os, tempfile
from threading import Thread, Timer
from .. import Target
from ..core import features
from ..core.util import Bindable
from ..core.config import config, ConfigDict
from ..amp import AmpController
from . import gui
from .key_binding import RemoteControlService, VolumeChanger


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
        super().update("Connecting ...", self.target.prompt)
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

    def on_feature_change(self, key, value, *args): # bound to target
        if key in (config.volume, config.muted, config.power): self.update_icon()

    def update_icon(self):
        self.target.schedule(self._update_icon, requires=(config.muted, config.volume, config.power))

    def _update_icon(self):
        volume = self.target.features[config.volume]
        if not getattr(self.target,config.power): self.set_icon("power")
        elif getattr(self.target,config.muted) or volume.get() == volume.min:
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
        notification_whitelist = config.getlist("Tray","notification_whitelist")
        notification_blacklist = config.getlist("Tray","notification_blacklist")
        create_notification = lambda f: \
            NumericNotification(f) if isinstance(f, features.NumericFeature) else TextNotification(f)
        self._notifications = {key:create_notification(f) for key,f in list(self.target.features.items())
            if f.key not in notification_blacklist
            and ("*" in notification_whitelist or self.f.key in notification_whitelist)}
        self.target.preload_features.add(config.volume)
        self.target.bind(on_feature_change = self.show_notification_on_feature_change)
    
    def show_notification(self, key): key in self._notifications and self._notifications[key].show()
    
    def on_key_press(self,*args,**xargs):
        self.show_notification(config.volume)
        super().on_key_press(*args,**xargs)

    def show_notification_on_feature_change(self, key, value, prev): # bound to target
        if key in self._notifications: self._notifications[key].update()
        if prev is not None: self.show_notification(key)

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
            if volume.isset(): volume.send(volume.get()+self.scroll_delta*steps)
        except ConnectionError: pass

    def on_scroll_down(self, steps):
        volume = self.target.features[config.volume]
        try:
            if volume.isset(): volume.send(volume.get()-self.scroll_delta*steps)
        except ConnectionError: pass
    
    def poweron(self, force=False):
        """ poweron target """
        if force or self.config["control_power_on"]: super().poweron()
        
    @property # read by poweroff()
    def can_poweroff(self): return self.config["control_power_off"] and super().can_poweroff
    

class NotifyPoweroff:
    """ Adds a notification warning to poweroff when on_idle """
    notification_timeout = 10

    def __init__(self, *args, **xargs):
        super().__init__(*args, **xargs)
        self.target.preload_features.add("name")
        self.target.bind(
            on_start_playing = self.close_popup,
            on_poweroff = self.close_popup,
            on_disconnected = self.close_popup)
        self._n = gui.Notification()
        self._n.add_action("cancel", "Cancel", lambda *args,**xargs: None)
        self._n.add_action("ok", "OK", lambda *args,**xargs: self.poweroff())
        self._n.connect("closed", self.on_popup_closed)
        self._n.set_timeout(self.notification_timeout*1000)
    
    def on_popup_closed(self, *args):
        if self._n.get_closed_reason() == 1: # timeout
            self.poweroff()
    
    def on_target_idle(self): self.target.schedule(self._on_target_idle, requires=("name",))

    def _on_target_idle(self):
        if self.can_poweroff:
            self._n.update("Power off %s"%self.target.name)
            self._n.show()
        
    def close_popup(self):
        try: self._n.close()
        except: pass


class Main(NotificationMixin, NotifyPoweroff, VolumeChanger, TrayMixin, gui.GUI_Backend, AmpController):
    
    def mainloop(self):
        Thread(name="AmpController",target=lambda:AmpController.mainloop(self),daemon=True).start()
        gui.GUI_Backend.mainloop(self)


def main(args):
    target = Target(args.target, connect=False, verbose=args.verbose+1)
    with Icon(target) as icon:
        app = Main(target, icon=icon, verbose=args.verbose+1)
        rcs = RemoteControlService(app,verbose=args.verbose)
        with target, rcs: app.mainloop()

