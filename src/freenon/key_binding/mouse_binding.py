#!/usr/bin/env python3
# -*- coding: utf-8 -*- 

from pynput.mouse import Listener, Button, Controller
from .volume_changer import VolumeChanger
from ..config import config


VOLUP = getattr(Button,config["MouseBinding"]["vol_up"])
VOLDOWN = getattr(Button,config["MouseBinding"]["vol_down"])


class Main(VolumeChanger):

    def on_click(self, x, y, button, pressed):
        if button not in (VOLUP, VOLDOWN):
            return
        button = button == VOLUP # to bool
        if pressed:
            self.press(button)
        else:
            self.release(button)
            
    def __call__(self):
        print("WARNING: Mouse events that control the AVR are not being suppressed to other programs.")
        with Listener(on_click=self.on_click, suppress=False) as listener: #bug: suppress=True kills X
            listener.join()


def main():
    Main()()
    
if __name__ == "__main__":
    main()

