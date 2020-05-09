#!/usr/bin/env python3
# -*- coding: utf-8 -*- 

import sys, time, argparse, socket
from threading import Lock, Thread
from telnetlib import Telnet
from .config import config
from .config import FILE as CONFFILE
try: from .setup import DenonDiscoverer
except ImportError: pass


class AbstractDenonFeature(object):
    function = ""
    translation = {}
    
    def decodeVal(self, val):
        return self.translation[val]
        
    def encodeVal(self, val):
        return {val:key for key,val in self.translation.items()}[val]


class DenonFeature(AbstractDenonFeature):        
    features = []

    #def __init__(self): self.features= []
    
    def _poll(self, denon):
        return self._consume(denon, denon("%s?"%self.function))
    
    def __get__(self, denon, cls):
        if denon is None: return self
        try: return denon.__dict__[self._name]
        except KeyError: return self.poll(denon)
        
    def __set__(self, denon, value):
        denon.__dict__[self._name] = value
        cmd = "%s%s"%(self.function, self.encodeVal(value))
        denon(cmd)
    
    def __set_name__(self, cls, name):
        self._name = name
        self_ = self.__class__() # does not react on __get__
        self_._name = name
        self.features.append((cls, self_))
    
    def _consume(self, denon, cmd):
        """
        Update property according to @cmd
        @denon property owner
        """
        if not cmd.startswith(self.function): 
            raise Exception("Cannot handle `%s`."%cmd)
        param = cmd[len(self.function):]
        denon.__dict__[self._name] = self.decodeVal(param)
        return denon.__dict__[self._name]
        
    @classmethod
    def consume(self, denon, cmd):
        """
        Update attributes in object @denon using message @cmd from AVR
        @returns: (attrib name, old value, new value)
        """
        for cls, self_ in self.features:
            if cmd.startswith(self_.function) and issubclass(denon.__class__,cls):
                old = denon.__dict__.get(self_._name)
                new = self_._consume(denon, cmd)
                return self_._name, old, new
        return None, None, None
    
    @classmethod
    def poll_all(self, denon):
        """ refresh all DenonFeature attributes """
        for cls, self_ in self.features:
            self_._poll()
            

class DenonFeature_Maxvol(DenonFeature):
    function="MVMAX"
    
    _poll = lambda *args:None
    def decodeVal(self, val): pass # TODO
    def encodeVal(self, val): pass
    

class DenonFeature_Volume(DenonFeature):
    function = "MV"
    # TODO: value may be relative?
    
    @staticmethod
    def _roundVolume(vol):
        return .5*round(vol/.5)

    def decodeVal(self, val):
        return int(val.ljust(3,"0"))/10
        
    def encodeVal(self, val):
        vol = self._roundVolume(val)
        return "%03d"%(vol*10)
        
        
class DenonFeature_Power(DenonFeature):
    function = "PW"
    translation = {"ON":True,"STANDBY":False}
    
    
class DenonFeature_Muted(DenonFeature):
    function = "MU"
    translation = {"ON":True,"OFF":False}

    
    
class BasicDenon(object):
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
        self._telnet = Telnet(self.host,23,timeout=2)
        
    def _send(self, cmd):
        cmd = cmd.upper()
        self._telnet.write(("%s\n"%cmd).encode("ascii"))
        return cmd
        
    def _read(self, timeout=None):
        try: return self._telnet.read_until(b"\r",timeout=timeout).strip().decode()
        except socket.timeout: return None
        
    def __call__(self, cmd):
        """ 
        Send command to AVR
        """
        if self.verbose: print("[Denon cli] %s"%cmd, file=sys.stderr)
        if "?" not in cmd: return self._send(cmd)

        def _return(r):
            if self.verbose: print(r, file=sys.stderr)
            return r
        condition = lambda r: r.startswith(cmd.replace("?",""))

        self.lock.acquire()
        try:
            pos_received = len(self._received)
            cmd = self._send(cmd)
            for i in range(15):
                pos_received_new = len(self._received)
                for r in self._received[pos_received:pos_received_new]:
                    if condition(r): 
                        self._received.remove(r)
                        return _return(r)
                pos_received = pos_received_new
                r = self._read(2)
                if not r and i>5: # timeout #TODO
                    sys.stderr.write("(timeout) ")
                    break
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
            r = self._read(5)
            if r: self._received.append(r)


class Denon(BasicDenon):
    """ Mapping of commands into python methods """

    maxvol = DenonFeature_Maxvol()
    volume = DenonFeature_Volume()
    muted = DenonFeature_Muted()
    is_running = DenonFeature_Power()

    def poweron(self,force=False):
        if not force and not config.getboolean("AVR","control_power_on") or self.is_running:
            return 0
        self.is_running = True
        time.sleep(3) #TODO
        return 1

    def connected(self):
        try: self.connect()
        except (ConnectionError, socket.timeout, socket.gaierror, socket.herror): return False
        else: return True
    
    def wait_for_connection(self):
        while not self.connected(): time.sleep(3)
        
    def poweron_wait(self):
        """ wait for connection and power on """
        self.wait_for_connection()
        return self.poweron()

    def poweroff(self, force=False):
        if not force and not config.getboolean("AVR","control_power_off"): return 0
        self.is_running = False
        return 1
        
    def consume(self, cmd):
        return DenonFeature.consume(self, cmd)
        
    def poll_all(self):
        DenonFeature.poll_all(self)


class CLI(object):
    
    def __init__(self):
        parser = argparse.ArgumentParser(description='Controller for Denon AVR - CLI')
        parser.add_argument("command", nargs="*", type=str, help='Denon command')
        parser.add_argument('--host', type=str, default=None, help='AVR IP or hostname')
        parser.add_argument('-f','--follow', default=False, action="store_true", help='Monitor AVR messages')
        parser.add_argument("-v",'--verbose', default=False, action='store_true', help='Verbose mode')
        self.args = parser.parse_args()
        
    def __call__(self):
        denon = BasicDenon(self.args.host, verbose=self.args.verbose)
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
                denon._send(cmd)
            

main = lambda:CLI()()
if __name__ == "__main__":
    main()

