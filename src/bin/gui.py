#!/usr/bin/env python3
import argparse, sys, math, pkgutil, io, wx
from threading import Thread
from PIL import Image
from .. import Amp, NAME, amp_features
from ..amp import require
from ..amp_controller import AmpEvents, AmpController
from ..key_binding import RemoteControlService, VolumeChanger
from .. import ui
from ..config import config


try:
    assert(config["GUI"].get("backend") == "gtk")
    ui.loadgtk()
except (AssertionError, ImportError): ui.loadwx()
else: ui.init(NAME)


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
            message=str(feature.get() if feature.isset() else None),
            value=feature.get() if feature.isset() else None,
            min=feature.min,
            max=feature.max)
    

class GUI_Backend:
    
    def __init__(self, *args, **xargs):
        super().__init__(*args, **xargs)
        self._app = wx.App()

    def mainloop(self):
        if ui.backend != "wx": Thread(target=ui.mainloop, name="ui.mainloop", daemon=True).start()
        self._app.MainLoop()
    

class NotificationMixin(object):

    def __init__(self,*args,**xargs):
        super().__init__(*args,**xargs)
        self._notify_events = config.get("GUI","notify_events")
        self._notifications = {key:self._createNotification(f)
            for key,f in list(self.amp.features.items())+[(None,None)]}
        self.amp.preload_features.add("volume")
    
    def _createNotification(self, feature):
        if isinstance(feature, amp_features.NumericFeature): N = NumericFeatureNotification
        elif feature is None: N = TextNotification
        else: N = TextFeatureNotification
        n = N(self.amp.name)
        n.update(feature)
        n.set_urgency(2)
        n.set_timeout(config.getint("GUI","notification_timeout"))
        return n
    
    def update_notification(self, attr, val=None):
        n = self._notifications[attr]
        f = self.amp.features.get(attr)
        n.update(f or val)
        return n

    def press(self,*args,**xargs): # TODO: rename to on_press
        self._notifications["volume"].show()
        super().press(*args,**xargs)

    def on_change(self, attr, value): # amp change
        if attr != "maxvol" and (
                self._notify_events == "all"
                or self._notify_events == "all_implemented" and attr
                or attr in self._notify_events.split(", ")):
            self.update_notification(attr, value).show()
        super().on_change(attr,value)

    def on_scroll(self, *args, **xargs):
        self._notifications["volume"].show()
        super().on_scroll(*args,**xargs)
        

class Tray(object):

    def on_connect(self): # amp connect
        super().on_connect()
        self.updateIcon()

    def on_disconnected(self): # amp disconnect
        self.icon.hide()
        super().on_disconnected()
        
    def on_change(self, attr, value): # amp change
        super().on_change(attr,value)
        if attr in ("volume","muted","maxvol"): self.updateIcon()
            
    def __init__(self, *args, **xargs):
        super().__init__(*args,**xargs)
        self.scroll_delta = config.getfloat("GUI","tray_scroll_delta")
        self.icon = ui.Icon()
        self.icon.bind(on_scroll_up=self.on_scroll_up, on_scroll_down=self.on_scroll_down)
    
    @require("muted","volume","maxvol")
    def updateIcon(self):
        icons = ["audio-volume-low","audio-volume-medium","audio-volume-high"]
        volume = 0 if self.amp.muted else self.amp.volume

        #self.icon.set_tooltip_text("Volume: %0.1f\n%s"%(volume,self.amp.name))
        if self.amp.muted or volume == 0:
            self._set_icon_by_name("audio-volume-muted")
        else:
            icon_idx = math.ceil(volume/self.amp.maxvol *len(icons))-1
            self._set_icon_by_name(icons[icon_idx])
        self.icon.show()
    
    def _set_icon_by_name(self, name):
        if getattr(self,"_icon_name",None) == name: return
        self._icon_name = name
        image_data = pkgutil.get_data(
            __name__,"../share/icons/24/%s-dark.png"%name)
        icon = Image.open(io.BytesIO(image_data))
        self.icon.set_icon(icon, name)
    
    @require("volume")
    def on_scroll_up(self, steps):
        volume = self.amp.volume+self.scroll_delta*steps
        self.amp.volume = volume

    @require("volume")
    def on_scroll_down(self, steps):
        volume = self.amp.volume-self.scroll_delta*steps
        self.amp.volume = volume
    

class Main(NotificationMixin, VolumeChanger, Tray, AmpEvents, GUI_Backend): pass


def main():    
    parser = argparse.ArgumentParser(description='%s tray icon'%NAME)
    parser.add_argument('--verbose', '-v', action='count', default=0, help='Verbose mode')
    args = parser.parse_args()
    
    amp = Amp(verbose=args.verbose+1)
    ac = AmpController(amp, verbose=args.verbose+1)
    program = Main(amp)
    try:
        Thread(name="Amp",target=ac.mainloop,daemon=True).start()
        RemoteControlService(program,verbose=args.verbose)()
        program.mainloop()
    finally:
        try: program.icon.__del__()
        except: pass


if __name__ == "__main__":
    main()

