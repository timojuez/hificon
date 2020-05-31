# -*- coding: utf-8 -*-
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import GLib, Notify
import time
from threading import Thread
from .. import Amp
from ..config import config


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

    def __init__(self, on_volume_change=None):
        if on_volume_change: self.on_volume_change = on_volume_change
        self.amp = Amp(on_avr_change=self.on_avr_change)#(cls="BasicAmp")
        self.amp.connect() #FIXME
        self.interval = config.getfloat("KeyEventHandling","interval")/1000
        self.button = None
        self._firing = False
        
    def press(self, button):
        """ start sending volume events to AVR """
        self.keys_pressed += 1
        if self.keys_pressed <= 0: return
        self.button = button
        self.fire_volume()
        
    def on_avr_change(self, attr, value):
        if attr != "volume": return
        self.on_volume_change(value, by_bound_keys=self._firing)
        self._firing = False
        if self.keys_pressed <= 0: return
        if self.interval: time.sleep(self.interval)
        self.fire_volume()
        
    def fire_volume(self):
        for _ in range(100):
            self._firing = True
            try: self.amp.volume += config.getfloat("KeyEventHandling","step")*(int(self.button)*2-1)
            except ConnectionError:
                self._firing = False
                time.sleep(20)
            else: break

    def release(self, button):
        """ button released """
        self.keys_pressed -= 1
        if self.keys_pressed != 0: return
        return self._stop()
        
    def _stop(self):
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

    def on_volume_change(self, volume, by_bound_keys):
        if not by_bound_keys and not config.getboolean("KeyEventHandling","always_notify"): return
        try: volume = 0 if self.amp.muted else volume
        except ConnectionError: pass
        else:
            self._notification.update("Volume: %s"%volume,self.amp.host)
            self._notification.show()


class VolumeChanger(NotificationMixin, BasicVolumeChanger): pass

