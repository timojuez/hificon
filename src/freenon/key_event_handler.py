#!/usr/bin/env python3
# -*- coding: utf-8 -*- 

import os,time,argparse,json
from .denon import Denon
from .config import config


PIDFILE="/tmp/freenon_key_pid.json"
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
        """ listen for keys and stop when all released """
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
        
        
class Main(VolumeChanger):

    def __init__(self):
        parser = argparse.ArgumentParser(description='Call this to handle volume button press and release events')
        group1 = parser.add_mutually_exclusive_group(required=True)
        group1.add_argument("--up", action="store_true", default=False, help="Volume up key")
        group1.add_argument("--down", action="store_true", default=False, help="Volume down key")
        group2 = parser.add_mutually_exclusive_group(required=True)
        group2.add_argument("--pressed", action="store_true", default=False, help="Key pressed")
        group2.add_argument("--released", action="store_true", default=False, help="Key released")
        self.args = parser.parse_args()
        super(Main,self).__init__()

    def __call__(self):
        func = self.press if self.args.pressed else self.releasePoll
        func(self.args.up)
    
    def press(self, button):
        if self.load():
            self.release(None)
        with open(PIDFILE,"x") as fp:
            json.dump(dict(pid=os.getpid(), button=button),fp)
        self.set_button(button)
        self.start()

    def load(self):
        try:
            with open(PIDFILE) as fp:
                d = json.load(fp)
        except (FileNotFoundError, json.decoder.JSONDecodeError): return False
        self.pid = d["pid"]
        self.set_button(d["button"])
        return True
    
    def stop(self):
        os.remove(PIDFILE)
        try: os.kill(self.pid,9)
        except ProcessLookupError: pass
        return True
    
    def releasePoll(self, button):
        for i in range(3):
            if self.load():
                self.release(button)
                break
            time.sleep(0.05)


main = lambda:Main()()
if __name__ == "__main__":
    main()

