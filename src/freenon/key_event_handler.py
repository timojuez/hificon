#!/usr/bin/env python3
# -*- coding: utf-8 -*- 

import os,time,argparse,json
from .denon import Denon
from .config import config


PIDFILE="/tmp/freenon_key_pid.json"


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
    
    def press(self, cmd):
        #for i in range(20):
        #    if not os.path.exists(PIDFILE): break
        #    time.sleep(0.05)
        self._release()
        with open(PIDFILE,"x") as fp:
            json.dump(dict(pid=os.getpid(), cmd=cmd),fp)
            #fp.write(str(os.getpid()))
        interval = config.getfloat("KeyEventHandling","interval")/1000
        while True:
            self.denon(cmd)
            time.sleep(interval)

    def _release(self,cmd=None):
        """ 
        @cmd: release button for cmd @cmd. If None, release all buttons
        @return bool: success 
        """
        try:
            with open(PIDFILE) as fp:
                d = json.load(fp)
        except FileNotFoundError: return False
        pid = d["pid"]
        if cmd is not None and d["cmd"] != cmd: return True
        # on_button_release:
        try: os.kill(pid,9)
        except ProcessLookupError: pass
        os.remove(PIDFILE)
        return True
    
    def release(self, cmd):
        for i in range(20):
            if self._release(cmd):
                self.denon.poweron(True)
                break
            time.sleep(0.05)


main = lambda:Main()()
if __name__ == "__main__":
    main()

