#!/usr/bin/env python3
import argparse, sys, math
from threading import Thread
try:
    import gi
    gi.require_version('Gtk', '3.0')
    gi.require_version('Notify', '0.7')
    from gi.repository import Gtk, Gdk, Notify
except ImportError as e: print(repr(e), file=sys.stderr)
import pystray
from PIL import Image
from .. import Amp, NAME
from ..key_binding import RemoteControlService, VolumeChanger, _AmpEvents
from ..config import config


class NotificationMixin(object):

    def __init__(self,*args,**xargs):
        self._notify_events = config.get("GUI","notify_events")
        Notify.init(NAME)
        self._notifications = {}
        super().__init__(*args,**xargs)
        
    def _createNotification(self):
        notification = Notify.Notification()
        notification.set_urgency(2)
        notification.set_timeout(config.getint("GUI","notification_timeout"))
        notification.update("Connecting ...",self.amp.host)
        return notification
        
    def notify(self, attr, val=None):
        if attr == "maxvol": return
        try: name = self.amp.features[attr].name
        except (AttributeError, KeyError): name = attr
        if attr not in self._notifications: self._notifications[attr] = self._createNotification()
        n = self._notifications[attr]
        if isinstance(val,bool): val = {True:"On",False:"Off"}[val]
        if val is not None: n.update("%s: %s"%(name, val),self.amp.host)
        n.show()

    def press(self,*args,**xargs):
        self.notify("volume")
        super().press(*args,**xargs)

    def on_amp_change(self, attr, value):
        if (    self._notify_events == "all"
                or self._notify_events == "all_implemented" and attr
                or attr in self._notify_events.split(", ")):
            self.notify(attr,value)
        super().on_amp_change(attr,value)

    def on_scroll(self, *args, **xargs):
        try: volume = self.amp.volume
        except ConnectionError: volume = None
        self.notify("volume",volume)
        super().on_scroll(*args,**xargs)
        
icon_theme = Gtk.IconTheme.get_default()
class Icon(pystray.Icon):
    
    def connect(self,*args,**xargs):
        try: return self._appindicator.connect(*args,**xargs)
        except AttributeError: pass
        
    def set_icon_full(self,name,help):
        self.icon = Image.open(icon_theme.lookup_icon(name,48,0).get_filename())
        

class Tray(_AmpEvents):

    def mainloop(self): self.icon.run(setup=lambda _:None)

    def on_connect(self):
        super().on_connect()
        self.updateIcon()

    def on_disconnected(self):
        self.icon.visible = False
        super().on_disconnected()
        
    def on_amp_change(self, attr, value):
        super().on_amp_change(attr,value)
        if attr in ("volume","muted","maxvol"): self.updateIcon()
            
    def __init__(self, *args, **xargs):
        self.scroll_delta = config.getfloat("GUI","tray_scroll_delta")
        self.icon = Icon(NAME)
        self.icon.connect("scroll-event",self.on_scroll)
        super().__init__(*args,**xargs)
    
    def updateIcon(self):
        icons = ["audio-volume-low","audio-volume-medium","audio-volume-high"]
        try:
            muted = self.amp.muted
            volume = 0 if muted else self.amp.volume
            maxvol = self.amp.maxvol
        except ConnectionError: pass
        else: 
            #self.icon.set_tooltip_text("Volume: %0.1f\n%s"%(volume,self.amp.host))
            if muted or volume == 0:
                self.icon.set_icon_full("audio-volume-muted","muted")
            else:
                icon_idx = math.ceil(volume/maxvol *len(icons))-1
                self.icon.set_icon_full(icons[icon_idx],str(volume))
            self.icon.visible = True
    
    def on_scroll(self, icon, steps, direction):
        try:
            if direction == Gdk.ScrollDirection.UP:
                volume = self.amp.volume+self.scroll_delta*steps
            elif direction == Gdk.ScrollDirection.DOWN:
                volume = self.amp.volume-self.scroll_delta*steps
            else: return
            self.amp.volume = volume
        except ConnectionError: pass
        

class Main(NotificationMixin, VolumeChanger, Tray): pass


def main():    
    parser = argparse.ArgumentParser(description='%s tray icon'%NAME)
    parser.add_argument("-v",'--verbose', default=False, action='store_true', help='Verbose mode')
    args = parser.parse_args()
    
    amp = Amp(verbose=args.verbose)
    program = Main(amp)
    Thread(name="Amp",target=amp.mainloop,daemon=True).start()
    RemoteControlService(program)()
    program.mainloop()
        

if __name__ == "__main__":
    main()

