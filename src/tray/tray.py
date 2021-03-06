import sys, math, pkgutil, os, tempfile
from threading import Thread, Timer
from .. import Amp
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
        self.amp = feature.amp


class TextNotification(FeatureNotification, gui.Notification):
    
    def __init__(self, *args, **xargs):
        super().__init__(*args, **xargs)
        self.set_urgency(2)
        self.set_timeout(config.getint("Tray","notification_timeout"))
        super().update("Connecting ...", self.amp.prompt)
        self.amp.preload_features.add("name")
    
    @features.require("name")
    def update(self):
        if self.f.isset(): val = {True:"On",False:"Off"}.get(self.f.get(), self.f.get())
        else: return
        super().update("%s: %s"%(self.f.name, val), self.f.amp.name)

    @features.require("name")
    def show(self): super().show()


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
    
    def __init__(self, amp):
        self.amp = amp
        self._icon_name = None
        self.amp.bind(
            on_connect=self.update_icon,
            on_disconnected=self.set_icon,
            on_feature_change=self.on_feature_change)

    def bind(self, *args, **xargs):
        super().bind(*args, **xargs)
        self.set_icon()
        self.update_icon()

    def on_feature_change(self, key, value, *args): # bound to amp
        if key in (config.volume, config.muted, config.power): self.update_icon()

    @features.require(config.muted, config.volume, config.power)
    def update_icon(self):
        volume = self.amp.features[config.volume]
        if not getattr(self.amp,config.power): self.set_icon("power")
        elif getattr(self.amp,config.muted) or volume.get() == volume.min:
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
        self._notifications = {key:create_notification(f) for key,f in list(self.amp.features.items())
            if f.key not in notification_blacklist
            and ("*" in notification_whitelist or self.f.key in notification_whitelist)}
        self.amp.preload_features.add(config.volume)
        self.amp.bind(on_feature_change = self.show_notification_on_feature_change)
    
    def show_notification(self, key): key in self._notifications and self._notifications[key].show()
    
    def on_key_press(self,*args,**xargs):
        self.show_notification(config.volume)
        super().on_key_press(*args,**xargs)

    def show_notification_on_feature_change(self, key, value, prev): # bound to amp
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
        self.amp.preload_features.update((config.volume,config.muted))
        self.scroll_delta = config.getdecimal("Tray","tray_scroll_delta")
        icon.bind(on_change = self.on_icon_change)
        self.show()

    def on_icon_change(self, path, name):
        gui.ScalePopup(self.amp).set_image(path)
        self.set_icon(path, name)
    
    @features.require(config.volume)
    def on_scroll_up(self, steps):
        new_volume = getattr(self.amp,config.volume)+self.scroll_delta*steps
        setattr(self.amp, config.volume, new_volume)

    @features.require(config.volume)
    def on_scroll_down(self, steps):
        new_volume = getattr(self.amp,config.volume)-self.scroll_delta*steps
        setattr(self.amp, config.volume, new_volume)
    
    def poweron(self, force=False):
        """ poweron amp """
        if force or self.config["control_power_on"]: super().poweron()
        
    @property # read by poweroff()
    def can_poweroff(self): return self.config["control_power_off"] and super().can_poweroff
    

class NotifyPoweroff:
    """ Adds a notification warning to poweroff amp.on_idle """
    notification_timeout = 10

    def __init__(self, *args, **xargs):
        super().__init__(*args, **xargs)
        self.amp.preload_features.add("name")
        self.amp.bind(
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
    
    @features.require("name")
    def on_amp_idle(self):
        if self.can_poweroff:
            self._n.update("Power off %s"%self.amp.name)
            self._n.show()
        
    def close_popup(self):
        try: self._n.close()
        except: pass


class Main(NotificationMixin, NotifyPoweroff, VolumeChanger, TrayMixin, gui.GUI_Backend, AmpController):
    
    def mainloop(self):
        Thread(name="AmpController",target=lambda:AmpController.mainloop(self),daemon=True).start()
        gui.GUI_Backend.mainloop(self)


def main(args):
    amp = Amp(args.target, connect=False, verbose=args.verbose+1)
    with Icon(amp) as icon:
        app = Main(amp, icon=icon, verbose=args.verbose+1)
        with amp:
            if rcs := RemoteControlService(app,verbose=args.verbose): rcs()
            app.mainloop()

