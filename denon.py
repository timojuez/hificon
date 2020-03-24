#!/usr/bin/env python3
# -*- coding: utf-8 -*- 

import sys, time, subprocess, argparse, os, json, socket
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


def lazy_property(getter,setter):
    """ like property() but caches the response of getter """
    
    cache = []
    def getterL(name):
        if cache: return cache[0]
        cache.append(getter(name))
        return cache[0]
    def setterL(name, val):
        cache.clear()
        cache.append(val)
        setter(name, val)
    return property(getterL, setterL)
    

class DenonMethodsMixin(object):
    """ Mapping of commands into python methods """

    def poweron(self):
        if self("PW?") == 'PWON': return
        self("PWON")
        time.sleep(3)

    def poweron_wait(self):
        """ wait for connection and power on """
        telnet = self.telnet()
        while not telnet:
            telnet = self.telnet()
            time.sleep(3)
        telnet.close()
        self.poweron()

    def poweroff(self):
        self("PWSTANDBY")
        
    def getVolume(self):
        val = self("MV?")[2:]
        return int(val.ljust(3,"0"))/10

    def setVolume(self, vol):
        self("MV%02d"%vol)
        
    volume = lazy_property(getVolume,setVolume)
    
    def getMuted(self):
        return self("MU?") == "MUON"

    def setMuted(self, mute):
        self("MUON" if mute else "MUOFF")

    muted = lazy_property(getMuted,setMuted)
    

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

    def telnet(self):
        try:
            telnet = Telnet(self.host,23,timeout=2)
        except socket.gaierror:
            sys.stderr.write("Hostname not found.\n")
            return False
        except socket.timeout:
            sys.stderr.write("Timeout.\n")
            return False
        else: 
            return telnet

    def __call__(self, cmd):
        """ send command to AVR """
        telnet = self.telnet()
        if not telnet:
            sys.stderr.write("[Warning] dropping call\n")
            return
        try:
            if self.verbose: print("[Denon cli] %s"%cmd)
            telnet.write(("%s\n"%cmd).encode("ascii"))
            if "?" in cmd:
                r = telnet.read_until(b"\r",timeout=2).strip().decode()
                if self.verbose: print(r)
                return r
        finally: telnet.close()
        

class DenonSilentException(Denon):
    """ Denon class that catches the ConnectionError """
    
    def __call__(self, *args, **xargs):
        try:
            return super(DenonSilentException,self).__call__(*args,**xargs)
        except ConnectionError as e:
            print(str(e))
    

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

