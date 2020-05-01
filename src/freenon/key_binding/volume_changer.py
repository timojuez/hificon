# -*- coding: utf-8 -*-
import time 
from ..denon import Denon
from ..config import config


BUTTON2CMD = {True:"MVUP", False:"MVDOWN"}


class VolumeChanger(object):
    """ 
    Class for managing volume up/down while hot key pressed
    when both hot keys are being pressed, last one counts
    """

    def __init__(self):
        self.denon = Denon()
        self.interval = config.getfloat("KeyEventHandling","interval")/1000
        self.button = None

    def set_button(self, button):
        """ set or change currently pressed hot key before or while start() is running """
        self.button = button
        
    def start(self):
        """ listen for keys and stop when all released. Start in extra process or thread """
        while True:
            b = self.button
            if b is None: break
            self.denon(BUTTON2CMD[b])
            time.sleep(self.interval)

    def release(self, button):
        """ button released """
        if button is not None and self.button != button: return
        self.stop()
        
    def stop(self):
        self.button = None
        self.denon.poweron(True)
        
        
