#!/usr/bin/env python3
# -*- coding: utf-8 -*- 

import sys, time, argparse
from telnetlib import Telnet
from .config import config
from .setup import DenonDiscoverer


class Lazy_property(object):
    """ like property() but caches the response of getter """

    storage = dict()

    def __init__(self, fget, fset):
        self.fget = fget
        self.fset = fset

    def __get__(self, obj, type=None):
        if self in self.storage: return self.storage[self]
        val = self.storage[self] = self.fget(obj)
        return val

    def __set__(self, obj, value):
        self.fset(obj,value)
        self.storage[self] = value

    @classmethod
    def reset(self):
        self.storage.clear()

    
class DenonMethodsMixin(object):
    """ Mapping of commands into python methods """

    def poweron(self):
        if not config.getboolean("DEFAULT","control_power_on") or self("PW?") == 'PWON':
            return 0
        self("PWON")
        time.sleep(3) #TODO
        return 1

    def connected(self):
        try: self("")
        except OSError: return False
        else: return True
    
    def wait_for_connection(self):
        while not self.connected(): time.sleep(3)
        
    def poweron_wait(self):
        """ wait for connection and power on """
        self.wait_for_connection()
        return self.poweron()

    def poweroff(self):
        if not config.getboolean("DEFAULT","control_power_off"): return 0
        self("PWSTANDBY")
        return 1
        
    def getVolume(self):
        val = self("MV?")[2:]
        return int(val.ljust(3,"0"))/10

    def setVolume(self, vol):
        self("MV%02d"%vol)
        
    volume = Lazy_property(getVolume,setVolume)
    
    def getMuted(self):
        return self("MU?") == "MUON"

    def setMuted(self, mute):
        self("MUON" if mute else "MUOFF")

    muted = Lazy_property(getMuted,setMuted)
    
    def reset(self):
        """ resets lazy properties' cache """
        Lazy_property.reset()
        
    def running(self):
        """ return True if power is on """
        return self("PW?") == "PWON"
    
    is_running = Lazy_property(running,None)
    

class Denon(DenonMethodsMixin):
    """
    This class connects to the Denon AVR via LAN and executes commands (see Denon CLI protocol)
    @host is the AVR's hostname or IP.
    """

    def __init__(self, host=None, verbose=False):
        self.verbose = verbose
        self.host = host or config["DEFAULT"].get("Host") or DenonDiscoverer().denon
        if verbose: sys.stderr.write('AVR "%s"\n'%self.host)

    def __call__(self, cmd, ignoreMvmax=True):
        """ send command to AVR """
        with Telnet(self.host,23,timeout=2) as telnet:
            if self.verbose: print("[Denon cli] %s"%cmd, file=sys.stderr)
            telnet.write(("%s\n"%cmd).encode("ascii"))
            if "?" in cmd:
                for i in range(5):
                    r = telnet.read_until(b"\r",timeout=2).strip().decode()
                    if ignoreMvmax and r.startswith("MVMAX"): continue
                    if not r or r.startswith(cmd.replace("?","")): break
                if self.verbose: print(r, file=sys.stderr)
                return r
        

class CLI(object):
    
    def __init__(self):
        parser = argparse.ArgumentParser(description='Controller for Denon AVR - CLI')
        parser.add_argument("command", nargs="+", type=str, help='Denon command')
        parser.add_argument('--host', type=str, default=None, help='AVR IP or hostname')
        parser.add_argument("-v",'--verbose', default=False, action='store_true', help='Verbose mode')
        self.args = parser.parse_args()
        
    def __call__(self):
        denon = Denon(self.args.host, verbose=self.args.verbose)
        for cmd in self.args.command:
            r = denon(cmd)
            if r and not self.args.verbose: print(r)
            

main = lambda:CLI()()
if __name__ == "__main__":
    main()

