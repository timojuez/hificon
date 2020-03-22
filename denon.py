#!/usr/bin/env python3
# -*- coding: utf-8 -*- 

import sys, time, pulsectl, subprocess, argparse, os
from telnetlib import Telnet

CONFIG=os.path.expanduser("~/.denon_hostname")


class DenonDiscoverer(object):
    """
    Search local network for Denon AVR
    """

    def __init__(self, timeout=5):
        self.timeout = timeout
        try: self.findDevices()
        except Exception as e:
            sys.stderr.write("ERROR detecting Denon IP address.\n")
            raise

    def findDevices(self, try_=1):
        devices = subprocess.run(
            ["/usr/sbin/arp","-a"],stdout=subprocess.PIPE).stdout.decode().strip().split("\n")
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


class Denon(object):
    """
    This class connects to the Denon AVR via LAN and executes commands (see Denon CLI protocol)
    @host is the AVR's hostname or IP.
    """

    def __init__(self, host=None):
        self.host = host or self._detectHostname()
        self.connect()

    def _detectHostname(self):
        if os.path.exists(CONFIG):
            with open(CONFIG) as f:
                return f.read().strip()
        denons = DenonDiscoverer().denons
        if len(denons) > 1: sys.stderr.write("WARNING: Denon device ambiguous: %s.\n"%(", ".join(denons)))
        host = denons[0]
        with open(CONFIG,"w") as f:
            f.write(host)
        return host

    def connect(self):
        sys.stderr.write("Connecting to %s.\n"%self.host)
        self.telnet = Telnet(self.host,23,timeout=2)
    
    @property
    def is_connected(self):
        try: self.telnet.write(b"TEST\n")
        except OSError: return False
        else: return True

    def _requireConnection(func):
        def f(self,*args,**xargs):
            if self.is_connected or self.connect() and self.is_connected:
                return func(self,*args,**xargs)
            else: 
                sys.stderr.write("WARNING: No connection. Dropped %s(%s).\n"
                    %(func, ", ".join(args)) )
        return f
    
    @_requireConnection
    def __call__(self, *cmds, verbose=False):
        """ send command to AVR """
        cmd = "\n".join(cmds)
        if verbose: print(cmd)
        self.telnet.write(("%s\n"%cmd).encode("ascii"))
        if "?" in cmd:
            r = self.telnet.read_until(b"\r",timeout=2).strip().decode()
            if verbose: print(r)
            return r

    @_requireConnection
    def require_poweron(self):
        if self("PW?") == 'PWON': return
        self("PWON")
        time.sleep(3)
        

class CLI(object):
    
    def __init__(self):
        parser = argparse.ArgumentParser(description='Controller for Denon AVR - CLI')
        parser.add_argument("command", nargs="+", type=str, help='Denon command')
        parser.add_argument('--host', type=str, default=None, help='AVR IP or hostname')
        parser.add_argument("-v",'--verbose', default=False, action='store_true', help='Verbose mode')
        self.args = parser.parse_args()
        
    def __call__(self):
        denon = Denon(self.args.host)
        for cmd in self.args.command:
            r = denon(cmd, verbose=self.args.verbose)
            if r: print(r)
            
        
if __name__ == "__main__":
    CLI()()

