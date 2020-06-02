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
        if on_volume_change: self.on_volume_change = on_volume_change
        self.interval = config.getfloat("KeyEventHandling","interval")/1000
        self.step = config.getfloat("KeyEventHandling","step")
        self.button = None
        self._last_set = None
        self.amp = Amp(on_change=self.on_amp_change,on_connect=self.on_amp_connect,verbose=verbose)
        self.amp.connect() #FIXME
        
    def press(self, button):
        """ start sending volume events to amp """
        self.keys_pressed += 1
        if self.keys_pressed <= 0: return
        self.button = button
        self.fire_volume()
    
    def on_amp_connect(self):
        try: # preload values
            self.amp.muted
            self.amp.volume
        except ConnectionError as e: print(repr(e), file=sys.stderr)
        
    def on_amp_change(self, attr, value):
        if attr != "volume": return
        self.on_volume_change(value, by_bound_keys = value==self._last_set)
        if value != self._last_set: return
        self._last_set = None
        if self.keys_pressed <= 0: return
        if self.interval: time.sleep(self.interval)
        self.fire_volume()
        
    def fire_volume(self):
        for _ in range(100):
            if self.keys_pressed <= 0: return
            try:
                self._last_set = self.amp.volume + self.step*(int(self.button)*2-1)
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
        
    def on_volume_change(self, volume, by_bound_keys): pass


class NotificationMixin(object):

    def __init__(self,*args,**xargs):
        Notify.init("Freenon")
        self._notification = Notify.Notification()
        self._notification.set_urgency(2)
        self._notification.set_timeout(config.getint("KeyEventHandling","notification_timeout"))
        self._notification.set_hint("x",GLib.Variant.new_int32(50))
        self._notification.set_hint("y",GLib.Variant.new_int32(100))
        #self._notification.set_location(50,100)
        super().__init__(*args,**xargs)
        
    def press(self,*args,**xargs):
        self.notify()
        super().press(*args,**xargs)

    def on_volume_change(self, volume, by_bound_keys):
        if not by_bound_keys and not config.getboolean("KeyEventHandling","always_notify"): return
        self.notify()
        
    def notify(self):
        try: volume = 0 if self.amp.muted else self.amp.volume
        except ConnectionError: self._notification.update("No connection.",self.amp.host)
        else: self._notification.update("Volume: %s"%volume,self.amp.host)
        self._notification.show()


class VolumeChanger(NotificationMixin, BasicVolumeChanger): pass


class VolumeService(json_service.JsonService):

    def __init__(self, **xargs):
        print("Key Binding Service")
        self.vc = VolumeChanger(**xargs)
        super().__init__(port=ipc_port)
        
    def on_read(self, data):
        if data["func"] not in ("press","release") or not isinstance(data["button"],bool):
            return print("[%s] invalid message."%self.__class__.__name__, file=sys.stderr)
        getattr(self.vc, data["func"])(data["button"])
        

send = lambda e: json_service.send(x, port=ipc_port)
    

def main():
    VolumeService().mainloop()
    
if __name__ == "__main__":
    main()

