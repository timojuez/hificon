#!/usr/bin/env python3
import argparse, sys, math, pkgutil, io, wx
from threading import Thread
from PIL import Image
from .. import Amp, NAME
from ..amp import require
from ..amp_controller import AmpEvents, AmpController
from ..key_binding import RemoteControlService, VolumeChanger
from .. import ui
from ..config import config


class GUI_Backend:
    
    def __init__(self, *args, **xargs):
        super().__init__(*args, **xargs)
        self._app = wx.App()
        if ui.backend != "wx": ui.init(NAME)

    def mainloop(self):
        if ui.backend != "wx": ui.mainloop() # Thread(target=ui.mainloop, name="ui.mainloop", daemon=True).start()
        self._app.MainLoop()
    

class NotificationMixin(object):

    def __init__(self,*args,**xargs):
        super().__init__(*args,**xargs)
        self._notify_events = config.get("GUI","notify_events")
        self._notifications = {key:self._createNotification()
            for key in list(self.amp.features.keys())+[None]}
        self.amp.preload_features.add("volume")
    
    def _createNotification(self):
        notification = ui.Notification()
        notification.set_urgency(2)
        notification.set_timeout(config.getint("GUI","notification_timeout"))
        notification.update("Connecting ...",self.amp.name)
        notification.connect_icon(self.icon)
        return notification
    
    def notify(self, attr, val=None):
        if attr == "maxvol": return
        try: name = self.amp.features[attr].name
        except (AttributeError, KeyError): name = attr
        n = self._notifications[attr]
        if isinstance(val,bool): val = {True:"On",False:"Off"}[val]
        if val is not None: n.update("%s: %s"%(name, val),self.amp.name)
        n.show()

    def press(self,*args,**xargs):
        self.notify("volume", self.amp.volume if self.amp.features["volume"].isset() else None)
        super().press(*args,**xargs)

    def on_change(self, attr, value): # amp change
        if (    self._notify_events == "all"
                or self._notify_events == "all_implemented" and attr
                or attr in self._notify_events.split(", ")):
            self.notify(attr,value)
        super().on_change(attr,value)

    def on_scroll(self, *args, **xargs):
        self.notify("volume", self.amp.volume if self.amp.features["volume"].isset() else None)
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
        muted = self.amp.muted
        volume = 0 if muted else self.amp.volume
        maxvol = self.amp.maxvol

        #self.icon.set_tooltip_text("Volume: %0.1f\n%s"%(volume,self.amp.name))
        if muted or volume == 0:
            self._set_icon_by_name("audio-volume-muted", "muted")
        else:
            icon_idx = math.ceil(volume/maxvol *len(icons))-1
            self._set_icon_by_name(icons[icon_idx], str(volume))
        self.icon.show()
    
    def _set_icon_by_name(self, name, help):
        image_data = pkgutil.get_data(
            __name__,"../share/icons/24/%s-dark.png"%name)
        icon = Image.open(io.BytesIO(image_data))
        self.icon.set_icon(icon, help)
    
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
    Thread(name="Amp",target=ac.mainloop,daemon=True).start()
    RemoteControlService(program,verbose=args.verbose)()
    program.mainloop()
        

if __name__ == "__main__":
    main()

