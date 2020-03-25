#!/usr/bin/env python3
# -*- coding: utf-8 -*- 

import sys, time, subprocess, argparse, os, json
from telnetlib import Telnet

CONFIG=os.path.expanduser("~/.denon_discoverer")


class DenonDiscoverer(object):
    """
    Search local network for Denon AVR
    """

    def __init__(self, timeout=5, usecache=True):
        self.timeout = timeout
        if usecache and os.path.exists(CONFIG):
            with open(CONFIG) as f:
                d = json.load(f)
                self.devices = d["devices"]
                self.denons = d["denons"]
                return
        self.findDevices()
        with open(CONFIG,"w") as f:
            json.dump(dict(devices=self.devices,denons=self.denons),f)

    def findDevices(self, try_=1):
        try:
            devices = subprocess.run(
                ["/usr/sbin/arp","-a"],stdout=subprocess.PIPE).stdout.decode().strip().split("\n")
        except Exception as e:
            sys.stderr.write("ERROR detecting Denon IP address.\n")
            raise
        devices = [e.split(" ",1)[0] for e in devices]
        denons = [d for d in devices if d.lower().startswith("denon")]
        if len(denons) == 0:
            sys.stderr.write("INFO: #%d No Denons found, retry...\n"%try_)
            sleep = 5
            if try_*sleep > self.timeout: raise TimeoutError("No Denon found.")
            time.sleep(sleep)
            return self.findDevices(try_=try_+1)
        self.devices = devices
        self.denons = denons


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
        if self("PW?") == 'PWON': return 0
        self("PWON")
        time.sleep(3)
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
        self("PWSTANDBY")
        
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
    

class Denon(DenonMethodsMixin):
    """
    This class connects to the Denon AVR via LAN and executes commands (see Denon CLI protocol)
    @host is the AVR's hostname or IP.
    """

    def __init__(self, host=None, verbose=False):
        self.verbose = verbose
        self.host = host or self._detectHostname()
        sys.stderr.write('AVR "%s"\n'%self.host)

    def _detectHostname(self):
        denons = DenonDiscoverer().denons
        if len(denons) > 1: sys.stderr.write("WARNING: Denon device ambiguous: %s.\n"%(", ".join(denons)))
        return denons[0]

    def __call__(self, cmd):
        """ send command to AVR """
        with Telnet(self.host,23,timeout=2) as telnet:
            if self.verbose: print("[Denon cli] %s"%cmd)
            telnet.write(("%s\n"%cmd).encode("ascii"))
            if "?" in cmd:
                for i in range(5):
                    r = telnet.read_until(b"\r",timeout=2).strip().decode()
                    if not r or r.startswith(cmd.replace("?","")): break
                if self.verbose: print(r)
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
            if r: print(r)
            
        
if __name__ == "__main__":
    CLI()()

