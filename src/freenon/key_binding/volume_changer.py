# -*- coding: utf-8 -*-
import time
from threading import Thread
from .. import Amp
from ..config import config


class VolumeChanger(object):
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
        self.amp = Amp(on_avr_change=self.on_avr_change, verbose=True)#(cls="BasicAmp")
        self.amp.connect() #FIXME
        self.button = None
        self._volume = None
        
    def press(self, button):
        """ start sending volume events to AVR """
        self.keys_pressed += 1
        if self.keys_pressed <= 0: return
        self.button = button
        self.fire_volume()
        
    def on_avr_change(self, attr, value):
        if attr != "volume": return
        self.on_volume_change(value)
        self.fire_volume()
        
    def fire_volume(self):
        if self.keys_pressed == 0: return
        for _ in range(100):
            try: self.amp.volume += config.getfloat("KeyEventHandling","step")*(int(self.button)*2-1)
            except ConnectionError: time.sleep(20)
            else: break

    def release(self, button):
        """ button released """
        self.keys_pressed -= 1
        if self.keys_pressed != 0 and button is not None and self.button != button: return
        return self._stop()
        
    def _stop(self):
        self.button = None
        Thread(target=self._poweron, name="poweron", daemon=False).start()
    
    def _poweron(self):
        try: self.amp.poweron(True)
        except ConnectionError: pass
        
    def on_volume_change(self, volume): pass
    
