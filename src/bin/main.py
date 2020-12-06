import argparse, sys, math, pkgutil, tempfile
from threading import Thread, Timer
from ..amp import features
from ..amp_controller import AmpEvents, AmpController
from ..key_binding import RemoteControlService, VolumeChanger
from ..config import config
from .setup import Setup
from .. import Amp, NAME, ui


class NotificationWithTitle:
    
    def __init__(self, subtitle, *args, **xargs):
        self._subtitle = subtitle
        super().__init__(*args, **xargs)


class TextNotification(NotificationWithTitle, ui.Notification):
    
    def __init__(self,*args,**xargs):
        super().__init__(*args,**xargs)
        TextNotification.update(self, "Connecting ...")

    def update(self, text): not text or super().update(text, self._subtitle)
    

class TextFeatureNotification(TextNotification):
    
    def update(self, feature):
        if feature.isset(): val = {True:"On",False:"Off"}.get(feature.get(), feature.get())
        else: return
        super().update("%s: %s"%(feature.name, val))


class NumericFeatureNotification(NotificationWithTitle, ui.GaugeNotification):
    
    def update(self, feature):
        self._f = feature
        super().update(
            title=feature.name,
            message=str("%0.1f"%feature.get() if feature.isset() else "..."),
            value=feature.get() if feature.isset() else feature.min,
            min=feature.min,
            max=feature.max)
            
    def show(self):
        if self._f.key == config.volume and ui.VolumePopup().visible: return
        self.update(self._f)
        super().show()


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


class RelevantAmpEvents(Icon, AmpEvents):

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
        self._notification_whitelist = config.getlist("GUI","notification_whitelist")
        self._notification_blacklist = config.getlist("GUI","notification_blacklist")
        self._notifications = {key:self._createNotification(f)
            for key,f in list(self.amp.features.items())+[(None,None)]}
        self.amp.preload_features.add(config.volume)
    
    def _createNotification(self, feature):
        if isinstance(feature, features.NumericFeature): N = NumericFeatureNotification
        elif feature is None: N = TextNotification
        else: N = TextFeatureNotification
        n = N(self.amp.name)
        n.update(feature)
        n.set_urgency(2)
        n.set_timeout(config.getint("GUI","notification_timeout"))
        return n
    
    def update_notification(self, key, val=None):
        n = self._notifications[key]
        f = self.amp.features.get(key)
        n.update(f or val)
        return n

    def on_key_press(self,*args,**xargs):
        self._notifications[config.volume].show()
        super().on_key_press(*args,**xargs)

    def on_feature_change(self, key, value, prev): # bound to amp
        if not (key in self.amp.preload_features and prev is None) \
            and key not in self._notification_blacklist and (
                "all" in self._notification_whitelist
                or "all_implemented" in self._notification_whitelist and key
                or key in self._notification_whitelist):
            self.update_notification(key, value).show()
        super().on_feature_change(key,value,prev)

    def on_scroll_up(self, *args, **xargs):
        self._notifications[config.volume].show()
        if self.amp.features[config.volume].isset():
            self._notifications[config.volume].update(self.amp.features[config.volume])
        super().on_scroll_up(*args,**xargs)
        
    def on_scroll_down(self, *args, **xargs):
        self._notifications[config.volume].show()
        if self.amp.features[config.volume].isset():
            self._notifications[config.volume].update(self.amp.features[config.volume])
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
    

class MainApp(NotificationMixin, VolumeChanger, TrayMixin, RelevantAmpEvents, ui.GUI_Backend):
    pass


class AmpController(AmpController):
    """ Adds a notification warning to poweroff on_amp_idle """
    poweroff_timeout = 10

    def __init__(self, *args, **xargs):
        super().__init__(*args, **xargs)
        self._n = ui.Notification()
        self._n.update("Power off %s"%self.amp.name)
        self._n.add_action("cancel", "Cancel", lambda *args,**xargs: None)
        self._n.add_action("ok", "OK", lambda *args,**xargs: self.amp.poweroff())
        self._n.connect("closed", self.closed)
        self._n.set_timeout(self.poweroff_timeout*1000)
    
    def closed(self, *args):
        if self._n.get_closed_reason() == 1: # timeout
            self.amp.poweroff()
        
    def on_amp_idle(self):
        if self.amp.can_poweroff: self._n.show()
        
    def on_start_playing(self):
        super().on_start_playing()
        try: self._n.close()
        except: pass
        

def main():
    parser = argparse.ArgumentParser(description='%s tray icon'%NAME)
    parser.add_argument('--setup', default=False, action="store_true", help='Run initial setup')
    parser.add_argument('--protocol', type=str, default=None, help='Amp protocol')
    parser.add_argument('--verbose', '-v', action='count', default=0, help='Verbose mode')
    args = parser.parse_args()
    
    if not Setup.configured() or args.setup: Setup.setup()
    
    amp = Amp(connect=False, protocol=args.protocol, verbose=args.verbose+1)
    app = MainApp(amp)
    ac = AmpController(amp, verbose=args.verbose+1)
    try:
        with amp:
            Thread(name="Amp",target=ac.mainloop,daemon=True).start()
            rcs = RemoteControlService(app,verbose=args.verbose)
            if rcs: rcs()
            app.mainloop()
    finally:
        try: app.icon.__del__()
        except: pass


if __name__ == "__main__":
    main()

