# -*- coding: utf-8 -*-
import time, sys
from threading import Thread
from .util import json_service
from .config import config

ipc_port = config.getint("KeyEventHandling","ipc_port")


class _AmpEvents(object):
    # TODO: move to .amp or __init__

    def __init__(self,amp):
        self.amp = amp
        amp.bind(
            on_connect=self.on_connect,
            on_disconnected=self.on_disconnected,
            on_change=self.on_amp_change,
        )
        
    def on_connect(self): pass
    def on_disconnected(self): pass
    def on_amp_change(self,*args,**xargs): pass


class VolumeChanger(_AmpEvents):
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

    def __init__(self, *args, **xargs):
        super().__init__(*args, **xargs)
        self.interval = config.getfloat("KeyEventHandling","interval")/1000
        self.step = config.getfloat("KeyEventHandling","step")
        self.button = None
        
    def press(self, button):
        """ start sending volume events to amp """
        self.keys_pressed += 1
        if self.keys_pressed <= 0: return
        self.button = button
        self.fire_volume()
    
    def on_amp_connect(self):
        super().on_amp_connect()
        try: # preload values
            self.amp.volume
        except ConnectionError as e: print(repr(e), file=sys.stderr)
        
    def on_amp_change(self, attr, value):
        super().on_amp_change(attr, value)
        if attr != "volume" or self.keys_pressed <= 0: return
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
        


def RemoteControlService(*args,**xargs):
    if ipc_port < 0: return
    return json_service.RemoteControlService(*args,port=ipc_port,func_whitelist=("press","release"),**xargs)
    

send = lambda e: json_service.send(e, port=ipc_port)
    
