#!/usr/bin/env python3
# -*- coding: utf-8 -*- 

from threading import Lock, Timer
from .denon import Denon
from pynput.mouse import Listener, Button, Controller


class Main(object):

    def __init__(self):
        self.lock = Lock()
        self.denon = Denon()
        
    def on_click(self, x, y, button, pressed):
        if button not in (Button.button8, Button.button9):
            self._lastaction = (x,y,button,pressed)
            return False
        if pressed: 
            if button == Button.button9: self.interval("MVUP")
            else: self.interval("MVDOWN")
        else:
            self.lock.acquire()
            try: self.timer.cancel()
            finally: self.lock.release()

    def interval(self,cmd):
        # TODO: instead of Timer create thread of key_event_handler
        self.lock.acquire()
        try:
            self.denon(cmd)
            self.timer = Timer(.03,self.interval,(cmd,))
            self.timer.start()
        finally: self.lock.release()
    
    def __call__(self):
        print("WARNING: Mouse events that control the AVR are not being suppressed to other programs.")
        mouse = Controller()
        while True:
            with Listener(on_click=self.on_click, suppress=True) as listener:
                listener.join()
            x,y,button,pressed = self._lastaction
            mouse.move(x,y)
            if pressed: mouse.press(button)
            else: mouse.release(button)


def main():
    Main()()
    
if __name__ == "__main__":
    main()

