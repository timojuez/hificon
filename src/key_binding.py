# -*- coding: utf-8 -*-
import time, sys
from threading import Thread, Lock
from contextlib import suppress
from .util import json_service
from .amp_controller import AmpEvents
from . import amp
from .config import config

ipc_port = config.getint("Service","ipc_port")


class VolumeChanger(AmpEvents):
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
        self.step = config.getdecimal("KeyEventHandling","step")
        self.button = None
        self._vol_lock = Lock()
        self.amp.preload_features.add("volume")
        
    @amp.features.require("volume")
    def on_key_press(self, button):
        """ start sending volume events to amp """
        self.keys_pressed += 1
        self.button = button
        with suppress(RuntimeError): self._vol_lock.release()
        if self.keys_pressed != 1: return # run the following once for all keys
        while self.keys_pressed > 0:
            self._vol_lock.acquire()
            if self.keys_pressed > 0:
                self.amp.volume += self.step*(int(self.button)*2-1)
                if self.interval: time.sleep(self.interval)
    
    def on_feature_change(self, key, value, *args): # amp change
        super().on_feature_change(key, value, *args)
        if key != "volume" or self.keys_pressed <= 0: return
        with suppress(RuntimeError): self._vol_lock.release()

    def on_key_release(self, button):
        """ button released """
        self.keys_pressed -= 1
        if self.keys_pressed > 0: self.button = not button
        with suppress(RuntimeError): self._vol_lock.release()
        Thread(target=self.amp.poweron, args=(True,), name="poweron", daemon=False).start()


def RemoteControlService(*args,**xargs):
    if ipc_port < 0: return
    secure_mode = config.getboolean("Service","secure_mode")
    if not secure_mode: print("[WARNING] Service not running in secure mode", file=sys.stderr)
    whitelist = ("press","release") if secure_mode else None
    return json_service.RemoteControlService(*args,port=ipc_port,func_whitelist=whitelist,**xargs)
    

send = lambda e: json_service.send(e, port=ipc_port)
    
