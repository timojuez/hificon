#!/usr/bin/env python3
# -*- coding: utf-8 -*- 

import os,time,argparse,json
from filelock import FileLock
from .volume_changer import VolumeChanger


PIDFILE="/tmp/freenon_key_pid.json"


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
        self.lock = FileLock("%s.lock"%PIDFILE)

    def __call__(self):
        func = self.press if self.args.pressed else self.releasePoll
        func(self.args.up)
    
    def press(self, button):
        with self.lock:
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
        super(Main,self).stop()
        return True
    
    def releasePoll(self, button):
        with self.lock:
            for i in range(3):
                if self.load():
                    self.release(button)
                    break
                time.sleep(0.05)


main = lambda:Main()()
if __name__ == "__main__":
    main()

