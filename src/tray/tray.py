import sys, math, pkgutil, tempfile
from threading import Thread, Timer
from .. import Amp
from ..amp import features
from ..util.function_bind import Autobind
from ..config import config
from .key_binding import RemoteControlService, VolumeChanger
from .amp_controller import AmpController
from . import gtk as ui


class FeatureNotification:

    def __init__(self, feature, *args, **xargs):
        super().__init__(*args, **xargs)
        self.f = feature


class TextNotification(FeatureNotification, ui.Notification):
    
    def __init__(self, *args, **xargs):
        super().__init__(*args, **xargs)
        self.set_urgency(2)
        self.set_timeout(config.getint("GUI","notification_timeout"))
        super().update("Connecting ...", self.f.amp.name)
        
    def update(self):
        if self.f.isset(): val = {True:"On",False:"Off"}.get(self.f.get(), self.f.get())
        else: return
        super().update("%s: %s"%(self.f.name, val), self.f.amp.name)


class NumericNotification(FeatureNotification):
    
    def __init__(self, *args, **xargs):
        super().__init__(*args, **xargs)
        self._n = ui.GaugeNotification()
        self._n.set_timeout(config.getint("GUI","notification_timeout"))

    def update(self):
        self._n.update(
            title=self.f.name,
            message=str("%0.1f"%self.f.get() if self.f.isset() else "..."),
            value=self.f.get() if self.f.isset() else self.f.min,
            min=self.f.min,
            max=self.f.max)
            
    def show(self):
        if self.f.key == config.volume and ui.VolumePopup().visible: return
        self.update()
        self._n.show()
        

class Icon:
    """ Functions regarding loading images from src/share """
    
    _icon_path = tempfile.mktemp()

    def _getCurrentIconName(self):
        volume = self.amp.features[config.volume]
        if getattr(self.amp,config.muted) or volume.get() == volume.min:
            return "audio-volume-muted"
        else:
            icons = ["audio-volume-low","audio-volume-medium","audio-volume-high"]
            icon_idx = math.ceil(volume.get()/volume.max*len(icons))-1
            return icons[icon_idx]
    
    def getCurrentIconPath(self):
        name = self._getCurrentIconName()
        if getattr(self,"_icon_name",None) == name: return self._icon_path, name
        self._icon_name = name
        image_data = pkgutil.get_data(
            __name__,"../share/icons/scalable/%s-dark.svg"%name)
        with open(self._icon_path,"wb") as fp: fp.write(image_data)
        return self._icon_path, name

    def __del__(self):
        try: os.remove(self._icon_path)
        except: pass


class AmpEvents(Icon, Autobind):
    
    def __init__(self, obj, *args, **xargs):
        super().__init__(obj, *args, **xargs)
        self.amp = obj

    def on_connect(self): # amp connect
        super().on_connect()
        self.updateWidgets()

    def on_feature_change(self, key, value, *args): # bound to amp
        super().on_feature_change(key,value,*args)
        if key in (config.volume,config.muted): self.updateWidgets()

    @features.require(config.muted,config.volume)
    def updateWidgets(self):
        ui.VolumePopup(self.amp).set_image(self.getCurrentIconPath()[0])


class NotificationMixin(object):

    def __init__(self,*args,**xargs):
        super().__init__(*args,**xargs)
        notification_whitelist = config.getlist("GUI","notification_whitelist")
        notification_blacklist = config.getlist("GUI","notification_blacklist")
        create_notification = lambda f: \
            NumericNotification(f) if isinstance(f, features.NumericFeature) else TextNotification(f)
        self._notifications = {key:create_notification(f) for key,f in list(self.amp.features.items())
            if f.key not in notification_blacklist
            and ("*" in notification_whitelist or self.f.key in notification_whitelist)}
        for n in self._notifications.values(): n.update()
        self.amp.preload_features.add(config.volume)
    
    def show_notification(self, key): key in self._notifications and self._notifications[key].show()
    
    def on_key_press(self,*args,**xargs):
        self.show_notification(config.volume)
        super().on_key_press(*args,**xargs)

    def on_feature_change(self, key, value, prev): # bound to amp
        if key in self._notifications: self._notifications[key].update()
        if not (key in self.amp.preload_features and prev is None):
            self.show_notification(key)
        super().on_feature_change(key,value,prev)

    def on_scroll_up(self, *args, **xargs):
        self.show_notification(config.volume)
        super().on_scroll_up(*args,**xargs)
        
    def on_scroll_down(self, *args, **xargs):
        self.show_notification(config.volume)
        super().on_scroll_down(*args,**xargs)


class TrayMixin(Icon):

    def __init__(self, *args, **xargs):
        super().__init__(*args,**xargs)
        self.amp.preload_features.update((config.volume,config.muted))
        self.scroll_delta = config.getdecimal("GUI","tray_scroll_delta")
        self.icon = ui.Icon(self.amp)
        self.icon.bind(on_scroll_up=self.on_scroll_up, on_scroll_down=self.on_scroll_down)

    def on_connect(self): # amp connect
        super().on_connect()
        self.icon.show()
        
    def on_disconnected(self): # amp disconnect
        self.icon.hide()
        super().on_disconnected()
        
    @features.require(config.muted,config.volume)
    def updateWidgets(self):
        super().updateWidgets()
        self.icon.set_icon(*self.getCurrentIconPath())
    
    @features.require(config.volume)
    def on_scroll_up(self, steps):
        new_volume = getattr(self.amp,config.volume)+self.scroll_delta*steps
        setattr(self.amp, config.volume, new_volume)

    @features.require(config.volume)
    def on_scroll_down(self, steps):
        new_volume = getattr(self.amp,config.volume)-self.scroll_delta*steps
        setattr(self.amp, config.volume, new_volume)
    

class MainApp(NotificationMixin, VolumeChanger, TrayMixin, AmpEvents, ui.GUI_Backend):
    pass


class PoweroffOnIdle:
    """ Adds a notification warning to poweroff amp.on_idle """
    poweroff_timeout = 10

    def __init__(self, amp):
        self.amp = amp
        self.amp.bind(on_idle = self.on_amp_idle)
        self.amp.bind(on_start_playing = self.close_popup)
        self.amp.bind(on_poweroff = self.close_popup)
        self.amp.bind(on_disconnected = self.close_popup)
        self._n = ui.Notification()
        self._n.update("Power off %s"%self.amp.name)
        self._n.add_action("cancel", "Cancel", lambda *args,**xargs: None)
        self._n.add_action("ok", "OK", lambda *args,**xargs: self.amp.poweroff())
        self._n.connect("closed", self.on_popup_closed)
        self._n.set_timeout(self.poweroff_timeout*1000)
    
    def on_popup_closed(self, *args):
        if self._n.get_closed_reason() == 1: # timeout
            self.amp.poweroff()
        
    def on_amp_idle(self):
        if self.amp.can_poweroff: self._n.show()
        
    def close_popup(self):
        try: self._n.close()
        except: pass


def main(args):
    amp = Amp(connect=False, protocol=args.protocol, verbose=args.verbose+1)
    app = MainApp(amp)
    PoweroffOnIdle(amp)
    ac = AmpController(amp, verbose=args.verbose+1)
    try:
        with amp:
            Thread(name="Amp",target=ac.mainloop,daemon=True).start()
            if rcs := RemoteControlService(app,verbose=args.verbose): rcs()
            app.mainloop()
    finally:
        try: app.icon.__del__()
        except: pass

