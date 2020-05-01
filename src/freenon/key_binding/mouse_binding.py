#!/usr/bin/env python3
# -*- coding: utf-8 -*- 

from threading import Thread, Lock
from pynput.mouse import Listener, Button, Controller
from .key_event_handler import VolumeChanger


VOLUP = Button.button9
VOLDOWN = Button.button8


class Main(VolumeChanger):

    def __init__(self):
        self.thread = None
        self.lock = Lock()
        super(Main,self).__init__()
        
    def on_click(self, x, y, button, pressed):
        if button not in (VOLUP, VOLDOWN):
            return
        button = button == VOLUP # to bool
        self.lock.acquire()
        try:
            if pressed:
                self.set_button(button)
                if self.thread is None:
                    self.thread = Thread(target=self.start,daemon=True)
                    self.thread.start()
            else:
                self.release(button)
        finally: self.lock.release()
            
    def stop(self):
        super(Main,self).stop()
        self.thread.join()
        self.thread = None


    def __call__(self):
        print("WARNING: Mouse events that control the AVR are not being suppressed to other programs.")
        with Listener(on_click=self.on_click, suppress=False) as listener: #bug: suppress=True kills X
            listener.join()


def main():
    Main()()
    
if __name__ == "__main__":
    main()

