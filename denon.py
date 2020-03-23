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


def _requireConnection(func):
    """ decorator for functions inside Denon class """
    def f(self,*args,**xargs):
        if self.is_connected or self.connect():
            return func(self,*args,**xargs)
        else: 
            raise ConnectionError("No connection to AVR. Dropped %s(%s)."
                %(func, ", ".join(args)) )
    return f


class DenonMethodsMixin(object):
    """ Mapping of commands into python methods """

    @_requireConnection
    def poweron(self):
        if self("PW?") == 'PWON': return
        self("PWON")
        time.sleep(3)

    def poweron_wait(self):
        """ wait for connection and power on """
        if not self.is_connected:
            while not self.connect(): time.sleep(3)
        self.poweron()

    @_requireConnection
    def poweroff(self):
        self("PWSTANDBY")
        
    @_requireConnection
    def getVolume(self):
        return int(self("MV?")[2:])

    @_requireConnection
    def setVolume(self, vol):
        self("MV%d"%vol)
        
    volume = property(getVolume,setVolume)
    
    @_requireConnection
    def getMuted(self):
        return self("MU?") == "MUON"

    @_requireConnection
    def setMuted(self, mute):
        self("MUON" if mute else "MUOFF")

    muted = property(getMuted,setMuted)
    

class Denon(DenonMethodsMixin):
    """
    This class connects to the Denon AVR via LAN and executes commands (see Denon CLI protocol)
    @host is the AVR's hostname or IP.
    """

    def __init__(self, host=None, verbose=False):
        self.verbose = verbose
        self.host = host or self._detectHostname()
        #self.connect()

    def _detectHostname(self):
        denons = DenonDiscoverer().denons
        if len(denons) > 1: sys.stderr.write("WARNING: Denon device ambiguous: %s.\n"%(", ".join(denons)))
        return denons[0]

    def connect(self):
        sys.stderr.write("Connecting to %s... "%self.host)
        sys.stderr.flush()
        try:
            self.telnet = Telnet(self.host,23,timeout=2)
        except socket.gaierror:
            sys.stderr.write("Hostname not found.\n")
            return False
        except socket.timeout:
            sys.stderr.write("Timeout.\n")
            return False
        else: 
            sys.stderr.write("ok\n")
            return True
    
    @property
    def is_connected(self):
        try: self.telnet.write(b"TEST\n")
        except (OSError, AttributeError) as e: return False
        else: return True

    @_requireConnection
    def __call__(self, *cmds):
        """ send command to AVR """
        cmd = "\n".join(cmds)
        if self.verbose: print("[Denon cli] %s"%cmd)
        self.telnet.write(("%s\n"%cmd).encode("ascii"))
        if "?" in cmd:
            r = self.telnet.read_until(b"\r",timeout=2).strip().decode()
            if self.verbose: print(r)
            return r
        

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

