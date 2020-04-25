#!/usr/bin/env python3
# -*- coding: utf-8 -*- 

import os,time,argparse
from .denon import Denon
from .config import config


PIDFILE="/tmp/freenon_key.pid"


class Main(object):

    def __init__(self):
        parser = argparse.ArgumentParser(description='Call this to handle volume button press and release events')
        group1 = parser.add_mutually_exclusive_group(required=True)
        group1.add_argument("--up", action="store_true", default=False, help="Volume up key")
        group1.add_argument("--down", action="store_true", default=False, help="Volume down key")
        group2 = parser.add_mutually_exclusive_group(required=True)
        group2.add_argument("--pressed", action="store_true", default=False, help="Key pressed")
        group2.add_argument("--released", action="store_true", default=False, help="Key released")
        self.args = parser.parse_args()
        self.denon = Denon()

    def __call__(self):
        cmd = "MVUP" if self.args.up else "MVDOWN"
        func = self.press if self.args.pressed else self.release
        func(cmd)
    
    def press(self, *cmds):
        with open(PIDFILE,"w") as fp:
            fp.write(str(os.getpid()))
        interval = config.getfloat("KeyEventHandling","interval")/1000
        while True:
            for cmd in cmds: self.denon(cmd)
            time.sleep(interval)

    def release(self, *cmds):
        for i in range(500):
            if os.path.exists(PIDFILE):
                with open(PIDFILE) as fp: 
                    try: pid=int(fp.read().strip())
                    except ValueError: continue
                # on_button_release:
                os.kill(pid,9)
                os.remove(PIDFILE)
                self.denon.poweron(True)
                break
            time.sleep(0.05)


main = lambda:Main()()
if __name__ == "__main__":
    main()

