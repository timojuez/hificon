#!/usr/bin/env python3
import argparse, sys, math, pkgutil, io
import notify2 as Notify
from threading import Thread
try:
    import gi
    gi.require_version('Gdk', '3.0')
    from gi.repository import Gdk
except ImportError as e: print(repr(e), file=sys.stderr)
import pystray
from PIL import Image
from dbus.exceptions import DBusException
from .. import Amp, NAME
from ..amp import require
from ..amp_controller import AmpEvents, AmpController
from ..key_binding import RemoteControlService, VolumeChanger
from ..config import config


class NotificationMixin(object):

    def __init__(self,*args,**xargs):
        self._notify_events = config.get("GUI","notify_events")
        self._notifications = {}
        Notify.init(NAME)
        super().__init__(*args,**xargs)
        
    def _createNotification(self):
        notification = Notify.Notification("")
        notification.set_urgency(2)
        notification.set_timeout(config.getint("GUI","notification_timeout"))
        notification.update("Connecting ...",self.amp.name)
        return notification
        
    def notify(self, attr, val=None):
        if attr == "maxvol": return
        try: name = self.amp.features[attr].name
        except (AttributeError, KeyError): name = attr
        if attr not in self._notifications: self._notifications[attr] = self._createNotification()
        n = self._notifications[attr]
        if isinstance(val,bool): val = {True:"On",False:"Off"}[val]
        if val is not None: n.update("%s: %s"%(name, val),self.amp.name)
        try: n.show()
        except DBusException: # notify2 bug workaround
            Notify.init(NAME)
            n.show()

    def press(self,*args,**xargs):
        self.notify("volume")
        super().press(*args,**xargs)

    def on_change(self, attr, value): # amp change
        if (    self._notify_events == "all"
                or self._notify_events == "all_implemented" and attr
                or attr in self._notify_events.split(", ")):
            self.notify(attr,value)
        super().on_change(attr,value)

    def on_scroll(self, *args, **xargs):
        self.notify("volume")
        @require("volume")
        def go(amp): self.notify("volume",self.amp.volume)
        if not self.amp.features["volume"].isset(): go(self.amp)
        super().on_scroll(*args,**xargs)
        

class Icon(pystray.Icon):
    
    def connect(self,*args,**xargs):
        try: return self._appindicator.connect(*args,**xargs)
        except AttributeError: pass
        
    def set_icon_full(self,name,help):
        image_data = pkgutil.get_data(
            __name__,"../share/icons/24/%s-dark.png"%name)
        self.icon = Image.open(io.BytesIO(image_data))
        

class Tray(object):

    def mainloop(self): self.icon.run(setup=lambda _:None)

    def on_connect(self): # amp connect
        super().on_connect()
        self.updateIcon()

    def on_disconnected(self): # amp disconnect
        self.icon.visible = False
        super().on_disconnected()
        
    def on_change(self, attr, value): # amp change
        super().on_change(attr,value)
        if attr in ("volume","muted","maxvol"): self.updateIcon()
            
    def __init__(self, *args, **xargs):
        self.scroll_delta = config.getfloat("GUI","tray_scroll_delta")
        self.icon = Icon(NAME)
        self.icon.connect("scroll-event",self.on_scroll)
        super().__init__(*args,**xargs)
    
    @require("muted","volume","maxvol")
    def updateIcon(self):
        icons = ["audio-volume-low","audio-volume-medium","audio-volume-high"]
        muted = self.amp.muted
        volume = 0 if muted else self.amp.volume
        maxvol = self.amp.maxvol

        #self.icon.set_tooltip_text("Volume: %0.1f\n%s"%(volume,self.amp.name))
        if muted or volume == 0:
            self.icon.set_icon_full("audio-volume-muted","muted")
        else:
            icon_idx = math.ceil(volume/maxvol *len(icons))-1
            self.icon.set_icon_full(icons[icon_idx],str(volume))
        self.icon.visible = True
    
    @require("volume")
    def on_scroll(self, icon, steps, direction):
        if direction == Gdk.ScrollDirection.UP:
            volume = self.amp.volume+self.scroll_delta*steps
        elif direction == Gdk.ScrollDirection.DOWN:
            volume = self.amp.volume-self.scroll_delta*steps
        else: return
        self.amp.volume = volume
        

class Main(NotificationMixin, VolumeChanger, Tray, AmpEvents): pass


def main():    
    parser = argparse.ArgumentParser(description='%s tray icon'%NAME)
    parser.add_argument('--verbose', '-v', action='count', default=0, help='Verbose mode')
    args = parser.parse_args()
    
    amp = Amp(verbose=args.verbose+1)
    ac = AmpController(amp, verbose=args.verbose)
    program = Main(amp)
    Thread(name="Amp",target=ac.mainloop,daemon=True).start()
    RemoteControlService(program,verbose=args.verbose)()
    program.mainloop()
        

if __name__ == "__main__":
    main()

