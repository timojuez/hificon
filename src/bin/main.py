#!/usr/bin/env python3
import argparse, sys, math, pkgutil, tempfile
from threading import Thread, Timer
from ..amp import features
from ..amp_controller import AmpEvents, AmpController
from ..key_binding import RemoteControlService, VolumeChanger
from ..config import config
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
        super().update(
            title=feature.name,
            message=str("%0.1f"%feature.get() if feature.isset() else "..."),
            value=feature.get() if feature.isset() else feature.min,
            min=feature.min,
            max=feature.max)


class Icon:
    """ Functions regarding loading images from src/share """
    
    _icon_path = tempfile.mktemp()

    def _getCurrentIconName(self):
        icons = ["audio-volume-low","audio-volume-medium","audio-volume-high"]
        volume = 0 if self.amp.muted else self.amp.volume

        #self.icon.set_tooltip_text("Volume: %0.1f\n%s"%(volume,self.amp.name))
        if self.amp.muted or volume == 0:
            return "audio-volume-muted"
        else:
            icon_idx = math.ceil(volume/self.amp.features["volume"].max *len(icons))-1
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
        if key in ("volume","muted","maxvol"): self.updateWidgets()

    def updateWidgets(self):
        ui.VolumePopup.instance.set_image(self.getCurrentIconPath()[0])


class NotificationMixin(object):

    def __init__(self,*args,**xargs):
        super().__init__(*args,**xargs)
        self._notify_events = config.getlist("GUI","notify_events")
        self._notifications = {key:self._createNotification(f)
            for key,f in list(self.amp.features.items())+[(None,None)]}
        self.amp.preload_features.add("volume")
    
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
        self._notifications["volume"].show()
        super().on_key_press(*args,**xargs)

    def on_feature_change(self, key, value, prev): # bound to amp
        if not (key in self.amp.preload_features and prev is None) \
            and key != "maxvol" and (
                "all" in self._notify_events
                or "all_implemented" in self._notify_events and key
                or key in self._notify_events):
            self.update_notification(key, value).show()
        super().on_feature_change(key,value,prev)

    def on_scroll_up(self, *args, **xargs):
        self._notifications["volume"].show()
        if self.amp.features["volume"].isset():
            self._notifications["volume"].update(self.amp.features["volume"])
        super().on_scroll_up(*args,**xargs)
        
    def on_scroll_down(self, *args, **xargs):
        self._notifications["volume"].show()
        if self.amp.features["volume"].isset():
            self._notifications["volume"].update(self.amp.features["volume"])
        super().on_scroll_down(*args,**xargs)


class TrayMixin(Icon):

    def __init__(self, *args, **xargs):
        super().__init__(*args,**xargs)
        self.amp.preload_features.update(("volume","muted","maxvol"))
        self.scroll_delta = config.getdecimal("GUI","tray_scroll_delta")
        self.icon = ui.Icon(self.amp)
        self.icon.bind(on_scroll_up=self.on_scroll_up, on_scroll_down=self.on_scroll_down)

    def on_connect(self): # amp connect
        super().on_connect()
        self.icon.show()
        
    def on_disconnected(self): # amp disconnect
        self.icon.hide()
        super().on_disconnected()
        
    @features.require("muted","volume","maxvol")
    def updateWidgets(self):
        super().updateWidgets()
        self.icon.icon.set_icon_full(*self.getCurrentIconPath())
    
    @features.require("volume")
    def on_scroll_up(self, steps):
        volume = self.amp.volume+self.scroll_delta*steps
        self.amp.volume = volume

    @features.require("volume")
    def on_scroll_down(self, steps):
        volume = self.amp.volume-self.scroll_delta*steps
        self.amp.volume = volume
    

class MainApp(NotificationMixin, VolumeChanger, TrayMixin, RelevantAmpEvents, ui.GUI_Backend):
    pass


class AmpController(AmpController):
    """ Adds a notification warning to poweroff on_amp_idle """
    poweroff_timeout = 10

    def __init__(self, *args, **xargs):
        super().__init__(*args, **xargs)
        self._n = ui.Notification()
        self._n.update("Power off %s"%self.amp.name)
        if hasattr(self._n, "add_action"):
            self._n.add_action("Cancel", lambda *args,**xargs: self._poweroff_timer.cancel())
        self._n.set_timeout(self.poweroff_timeout*1000)
    
    def on_poweroff(self):
        try: self._n.close()
        except: pass
        super().on_poweroff()
        
    def on_amp_idle(self):
        if not self.amp.can_poweroff: return
        self._poweroff_timer = Timer(self.poweroff_timeout, super().on_amp_idle)
        self._poweroff_timer.start()
        self._n.show()
        

def main():    
    parser = argparse.ArgumentParser(description='%s tray icon'%NAME)
    parser.add_argument('--protocol', type=str, default=None, help='Amp protocol')
    parser.add_argument('--verbose', '-v', action='count', default=0, help='Verbose mode')
    args = parser.parse_args()
    
    amp = Amp(connect=False, protocol=args.protocol, verbose=args.verbose+1)
    app = MainApp(amp)
    ac = AmpController(amp, verbose=args.verbose+1)
    try:
        with amp:
            Thread(name="Amp",target=ac.mainloop,daemon=True).start()
            RemoteControlService(app,verbose=args.verbose)()
            app.mainloop()
    finally:
        try: app.icon.__del__()
        except: pass


if __name__ == "__main__":
    main()

