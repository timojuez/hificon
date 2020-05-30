# -*- coding: utf-8 -*-
import time
from threading import Thread, Lock
from .. import Amp
from ..config import config


BUTTON2CMD = {True:"MVUP", False:"MVDOWN"}


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

    def __init__(self):
        self.thread = None
        self.lock = Lock()
        self.amp = Amp(cls="BasicAmp")
        self.interval = config.getfloat("KeyEventHandling","interval")/1000
        self.button = None
        
    def press(self, button):
        """ start sending volume events to AVR """
        self.lock.acquire()
        try:
            self.button = button
            if self.thread is None:
                self.thread = Thread(target=self._loop,name="VolumeChanger",daemon=True)
                self.thread.start()
        finally: self.lock.release()
        
    def _loop(self):
        """ listen for keys and stop when all released. Start in extra process or thread """
        for _ in range(60): # max increase 60 steps for security
            b = self.button
            if b is None: break
            try: self.amp(BUTTON2CMD[b])
            except ConnectionError: pass
            time.sleep(self.interval)

    def release(self, button):
        """ button released """
        if button is not None and self.button != button: return
        return self._stop()
        
    def _stop(self):
        self.button = None
        if self.thread: 
            self.thread.join()
            self.thread = None
        Thread(target=self._poweron, name="poweron", daemon=False).start()
    
    def _poweron(self):
        try: self.amp.poweron(True)
        except ConnectionError: pass
        
