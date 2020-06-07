# -*- coding: utf-8 -*-
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import GLib, Notify
import time, sys
from threading import Thread
from . import Amp
from .util import json_service
from .config import config

ipc_port = config.getint("KeyEventHandling","ipc_port")


class BasicVolumeChanger(object):
    """ 
    Class for managing volume up/down while hot key pressed
    when both hot keys are being pressed, last one counts
    
    Example 1:
        button1=True
        button2=False
        press(button1)
        release(button1) #stops
    Example 2:
        press(button2)
        press(button1)
        release(button2) #skips
        release(button1) #stops
    """
    keys_pressed = 0

    def __init__(self, on_volume_change=None, verbose=False):
        super().__init__()
        if on_volume_change: self.on_volume_change = on_volume_change
        self.interval = config.getfloat("KeyEventHandling","interval")/1000
        self.step = config.getfloat("KeyEventHandling","step")
        self.button = None
        self._last_set = None
        self.amp = Amp(on_change=self.on_amp_change,on_connect=self.on_amp_connect,verbose=verbose)
        
    def press(self, button):
        """ start sending volume events to amp """
        super().press(button)
        self.keys_pressed += 1
        if self.keys_pressed <= 0: return
        self.button = button
        self.fire_volume()
    
    def on_amp_connect(self):
        try: # preload values
            self.amp.volume
        except ConnectionError as e: print(repr(e), file=sys.stderr)
        
    def on_amp_change(self, attr, value):
        super().on_amp_change(attr, value, by_bound_keys = value==self._last_set)
        if value != self._last_set: return
        self._last_set = None
        if self.keys_pressed <= 0: return
        if self.interval: time.sleep(self.interval)
        self.fire_volume()
        
    def fire_volume(self):
        for _ in range(100):
            if self.keys_pressed <= 0: return
            try:
                self._last_set = max(0,min(self.amp.maxvol,self.amp.volume + self.step*(int(self.button)*2-1)))
                self.amp.volume = self._last_set
            except ConnectionError:
                self._last_set = None
                time.sleep(20)
            else: break

    def release(self, button):
        """ button released """
        self.keys_pressed -= 1
        if not (self.keys_pressed <= 0): self.button = not button
        self.fire_volume()
        Thread(target=self._poweron, name="poweron", daemon=False).start()
    
    def _poweron(self):
        try: self.amp.poweron(True)
        except ConnectionError: pass
        

class NotificationMixin(object):

    def __init__(self,*args,**xargs):
        Notify.init("Freenon")
        self._notifications = {}
        
    def _createNotification(self):
        notification = Notify.Notification()
        notification.set_urgency(2)
        notification.set_hint("x",GLib.Variant.new_int32(50))
        notification.set_hint("y",GLib.Variant.new_int32(100))
        notification.set_timeout(config.getint("GUI","notification_timeout"))
        notification.update("Connecting ...",self.amp.host)
        return notification
        
    def press(self,*args,**xargs):
        self.notify("volume")

    def on_amp_change(self, attr, value, by_bound_keys=False):
        if (    config.get("GUI","notify_events") == "all"
                or config.get("GUI","notify_events") == "all_implemented" and attr
                or attr in config.get("GUI","notify_events").split(", ")):
            self.notify(attr,value)
        
    def notify(self, attr, val=None):
        if attr == "maxvol": return
        try: name = self.amp.features[attr].name
        except (AttributeError, KeyError): name = attr
        if attr not in self._notifications: self._notifications[attr] = self._createNotification()
        n = self._notifications[attr]
        if isinstance(val,bool): val = {True:"On",False:"Off"}[val]
        if val is not None: n.update("%s: %s"%(name, val),self.amp.host)
        n.show()


class VolumeChanger(BasicVolumeChanger, NotificationMixin): pass


class VolumeService(json_service.JsonService):

    def __init__(self, **xargs):
        print("Key Binding Service")
        self.vc = VolumeChanger(**xargs)
        super().__init__(port=ipc_port)
        
    def on_read(self, data):
        try:
            assert(data["func"] in ("press","release"))
            assert(isinstance(data["kwargs"]["button"],bool))
            func = getattr(self.vc, data["func"])
            kwargs = data["kwargs"]
        except:
            return print("[%s] invalid message."%self.__class__.__name__, file=sys.stderr)
        Thread(name="VolumeServiceAction",target=func,kwargs=kwargs,daemon=True).start()
        

send = lambda e: json_service.send(e, port=ipc_port)
    

def main():
    VolumeService().mainloop()
    
if __name__ == "__main__":
    main()

