# -*- coding: utf-8 -*-
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Notify', '0.7')
from gi.repository import GLib, Notify
import time, sys
from threading import Thread
from . import Amp
from .util import json_service
from .config import config

ipc_port = config.getint("KeyEventHandling","ipc_port")


class VolumeChangerMixin(object):
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

    def __init__(self, amp, *args, **xargs):
        super().__init__(*args, **xargs)
        self.interval = config.getfloat("KeyEventHandling","interval")/1000
        self.step = config.getfloat("KeyEventHandling","step")
        self.button = None
        self.amp = amp
        self.amp.bind(on_change=self.on_amp_change, on_connect=self.on_amp_connect)
        
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
        super().on_amp_change(attr, value)
        if self.keys_pressed <= 0: return
        if self.interval: time.sleep(self.interval)
        self.fire_volume()
        
    def fire_volume(self):
        for _ in range(100):
            if self.keys_pressed <= 0: return
            try: self.amp.volume += self.step*(int(self.button)*2-1)
            except ConnectionError: time.sleep(20)
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
        

class Notifier(object):

    def __init__(self):
        self._notify_events = config.get("GUI","notify_events")
        Notify.init("Freenon")
        self._notifications = {}
        
    def _createNotification(self):
        notification = Notify.Notification()
        notification.set_urgency(2)
        #notification.set_hint("x",GLib.Variant.new_int32(50))
        #notification.set_hint("y",GLib.Variant.new_int32(100))
        notification.set_timeout(config.getint("GUI","notification_timeout"))
        notification.update("Connecting ...",self.amp.host)
        return notification
        
    def press(self,*args,**xargs):
        self.notify("volume")

    def on_amp_change(self, attr, value):
        if (    self._notify_events == "all"
                or self._notify_events == "all_implemented" and attr
                or attr in self._notify_events.split(", ")):
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


class VolumeChanger(VolumeChangerMixin, Notifier): pass


class VolumeService(json_service.JsonService):

    def __init__(self, *args, **xargs):
        print("Key Binding Service")
        self.vc = VolumeChanger(*args, **xargs)
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
    amp = Amp()
    vs = VolumeService(amp)
    amp.mainloop(blocking=False)
    vs.mainloop()
    
if __name__ == "__main__":
    main()

