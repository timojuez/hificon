#!/usr/bin/env python3
# -*- coding: utf-8 -*- 

from threading import Lock, Timer
from pynput.mouse import Listener, Button, Controller
from .denon import Denon
from .config import config


VOLUP = Button.button9
VOLDOWN = Button.button8


class Main(object):

    def __init__(self):
        self.lock = Lock()
        self.denon = Denon()
        self.interval = config.getfloat("KeyEventHandling","interval")/1000
        
    def on_click(self, x, y, button, pressed):
        if button not in (VOLUP, VOLDOWN):
            return
            #self._lastaction = (x,y,button,pressed)
            #return False
        if pressed: 
            if button == VOLUP: self.interval_function("MVUP")
            else: self.interval_function("MVDOWN")
        else:
            self.lock.acquire()
            if not self.timer.isAlive(): raise
            try: self.timer.cancel()
            finally: self.lock.release()

    def interval_function(self,cmd):
        # TODO: instead of Timer create thread of key_event_handler
        self.lock.acquire()
        try:
            self.denon(cmd)
            self.timer = Timer(self.interval,self.interval_function,(cmd,))
            self.timer.start()
        finally: self.lock.release()
    
    def __call__(self):
        print("WARNING: Mouse events that control the AVR are not being suppressed to other programs.")
        mouse = Controller()
        while True:
            with Listener(on_click=self.on_click, suppress=False) as listener: #bug: suppress=True kills X
                listener.join()
            #x,y,button,pressed = self._lastaction
            #mouse.move(x,y)
            #if pressed: mouse.press(button)
            #else: mouse.release(button)


def main():
    Main()()
    
if __name__ == "__main__":
    main()

