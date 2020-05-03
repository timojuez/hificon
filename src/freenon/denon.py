#!/usr/bin/env python3
# -*- coding: utf-8 -*- 

import sys, time, argparse
from threading import Lock, Thread
from telnetlib import Telnet
from .config import config
from .config import FILE as CONFFILE
try: from .setup import DenonDiscoverer
except ImportError: pass


def roundVolume(vol):
    return .5*round(vol/.5)
    
    
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
        value = self.fset(obj,value)
        self.storage[self] = value

    @classmethod
    def reset(self):
        self.storage.clear()

    
class DenonMethodsMixin(object):
    """ Mapping of commands into python methods """

    def poweron(self,force=False):
        if not force and not config.getboolean("AVR","control_power_on") or self("PW?") == 'PWON':
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

    def poweroff(self, force=False):
        if not force and not config.getboolean("AVR","control_power_off"): return 0
        self("PWSTANDBY")
        return 1
        
    def getVolume(self):
        val = self("MV?")
        if not val: return None
        return int(val[2:].ljust(3,"0"))/10

    def setVolume(self, vol):
        vol = roundVolume(vol)
        self("MV%03d"%(vol*10))
        return vol
        
    volume = Lazy_property(getVolume,setVolume)
    
    def getMuted(self):
        return {"MUON":True, "MUOFF":False, None:None}[self("MU?")]

    def setMuted(self, mute):
        self("MUON" if mute else "MUOFF")
        return mute

    muted = Lazy_property(getMuted,setMuted)
    
    def reset(self):
        """ resets lazy properties' cache """
        Lazy_property.reset()
        
    def running(self):
        """ return True if power is on """
        return {"PWON":True, "PWSTANDBY":False, None:None}[self("PW?")]
    
    is_running = Lazy_property(running,None)
    

class Denon(DenonMethodsMixin):
    """
    This class connects to the Denon AVR via LAN and executes commands (see Denon CLI protocol)
    @host is the AVR's hostname or IP.
    """

    def __init__(self, host=None, verbose=False):
        self.verbose = verbose
        self.host = host or config["AVR"].get("Host") or \
            "DenonDiscoverer" in globals() and DenonDiscoverer().denon
        if not self.host: raise RuntimeError("Host is not set! Install autosetup or set AVR "
            "IP or hostname in %s."%CONFFILE)
        if verbose: sys.stderr.write('AVR "%s"\n'%self.host)
        self._received = []
        self.lock = Lock()
        self.connect()

    def connect(self):
        self.telnet = Telnet(self.host,23,timeout=2)

    def __call__(self, cmd, ignoreMvmax=True):
        """ 
        Send command to AVR
        """
        def _return(r):
            if self.verbose: print(r, file=sys.stderr)
            return r
        condition = lambda r: not (ignoreMvmax and r.startswith("MVMAX")) \
            and r.startswith(cmd.replace("?",""))

        self.lock.acquire()
        try:
            if self.verbose: print("[Denon cli] %s"%cmd, file=sys.stderr)
            pos_received = len(self._received)
            self.telnet.write(("%s\n"%cmd).encode("ascii"))
            if "?" not in cmd: return
            for r in self._received[pos_received:]:
                if condition(r): 
                    self._received.remove(r)
                    return _return(r)
            for i in range(15):
                r = self.telnet.read_until(b"\r",timeout=2).strip().decode()
                if not r: return r # timeout
                if condition(r): return _return(r)
                else: self._received.append(r)
            sys.stderr.write("WARNING: Got no answer for `%s`.\n"%cmd)                
        finally: self.lock.release()
        
    def read(self):
        """ Wait until a message has been received from AVR and return it """
        while True:
            self.lock.acquire()
            try:
                if self._received: return self._received.pop(0)
            finally: self.lock.release()
            r = self.telnet.read_until(b'\r',timeout=100).strip().decode()
            if r: self._received.append(r)
        

class CLI(object):
    
    def __init__(self):
        parser = argparse.ArgumentParser(description='Controller for Denon AVR - CLI')
        parser.add_argument("command", nargs="*", type=str, help='Denon command')
        parser.add_argument('--host', type=str, default=None, help='AVR IP or hostname')
        parser.add_argument('-f','--follow', default=False, action="store_true", help='Monitor AVR messages')
        parser.add_argument("-v",'--verbose', default=False, action='store_true', help='Verbose mode')
        self.args = parser.parse_args()
        
    def __call__(self):
        denon = Denon(self.args.host, verbose=self.args.verbose)
        for cmd in self.args.command:
            r = denon(cmd)
            if r and not self.args.verbose: print(r)
        if self.args.follow:
            def reader():
                while True: print("%s"%denon.read())
            Thread(target=reader,name="Reader",daemon=True).start()
            while True:
                try: cmd = input().strip()
                except KeyboardInterrupt: break
                denon.telnet.write(("%s\n"%cmd).encode("ascii"))
            

main = lambda:CLI()()
if __name__ == "__main__":
    main()

