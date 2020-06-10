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
        


class RemoteControlService(json_service.JsonService):
    """ 
    Opens a service on a port and executes calls on @obj when received 
    message schema: {"func": property_of_obj, "kwargs": {}}
    """

    def __init__(self, obj):
        self._obj = obj
        super().__init__(port=ipc_port)
        
    def on_read(self, data):
        try:
            assert(data["func"] in ("press","release"))
            assert(isinstance(data["kwargs"]["button"],bool))
            func = getattr(self._obj, data["func"])
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


