#!/usr/bin/env python3
# -*- coding: utf-8 -*- 

import argparse
from threading import Thread
from .. import Amp


class CLI(object):
    
    def __init__(self):
        parser = argparse.ArgumentParser(description='Controller for Network Amp - CLI')
        parser.add_argument("command", nargs="*", type=str, help='CLI command')
        parser.add_argument('--host', type=str, default=None, help='Amp IP or hostname')
        parser.add_argument('--protocol', type=str, default=None, help='Amp protocol')
        group = parser.add_mutually_exclusive_group(required=False)
        group.add_argument('--return', dest="ret", type=str, metavar="CMD", default=None, help='Return line that starts with CMD')
        group.add_argument('-f','--follow', default=False, action="store_true", help='Monitor amp messages')
        parser.add_argument("-v",'--verbose', default=False, action='store_true', help='Verbose mode')
        self.args = parser.parse_args()
        
    def __call__(self):
        amp = Amp(self.args.host, protocol=self.args.protocol, cls="BasicAmp", verbose=self.args.verbose)
        if self.args.follow or len(self.args.command) == 0:
            def reader():
                while True: print("%s"%amp.read())
            Thread(target=reader,name="Reader",daemon=True).start()
            for cmd in self.args.command:
                print(cmd)
                amp._send(cmd)
            while True:
                try: cmd = input().strip()
                except (KeyboardInterrupt, EOFError): break
                cmd = amp._send(cmd)
                #print("\r[sent] %s"%cmd)
            return
        for cmd in self.args.command:
            matches = lambda cmd:cmd.startswith(self.args.ret) if self.args.ret else None
            r = amp(cmd,matches=matches)
            if r and not self.args.verbose: print(r)
        

main = lambda:CLI()()
if __name__ == "__main__":
    main()

