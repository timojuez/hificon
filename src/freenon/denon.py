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
    
    def __get__(self, denon, cls):
        if denon is None: return self
        if not denon.connected: 
            raise ConnectionError("Variable `%s` is not available when AVR is disconnected."%self._name)
        try: return denon.__dict__[self._name]
        except KeyError: 
            self._poll(denon)
            return denon.__dict__[self._name]
        
    def __set__(self, denon, value):
        if denon.__dict__.get(self._name) == value: return
        denon.__dict__[self._name] = value
        self._send(denon)

    def __set_name__(self, cls, name):
        self._name = name
        self_ = self.__class__() # does not react on __get__
        self_._name = name
        self.features.append((cls, self_))
    
    def _isset(self, denon):
        return self._name in denon.__dict__
        
    def _poll(self, denon):
        return self._consume(denon, denon("%s?"%self.function))
    
    def _send(self, denon):
        cmd = "%s%s"%(self.function, self.encodeVal(denon.__dict__[self._name]))
        denon(cmd)
    
    def _consume(self, denon, cmd):
        """
        Update property according to @cmd
        @denon property owner
        """
        if not cmd.startswith(self.function): 
            raise ValueError("Cannot handle `%s`."%cmd)
        param = cmd[len(self.function):]
        old = denon.__dict__.get(self._name)
        denon.__dict__[self._name] = self.decodeVal(param)
        return old, denon.__dict__[self._name]
    
    @classmethod
    def _get_features(self, denon):
        for cls, self_ in self.features:
            if not issubclass(denon.__class__,cls): continue
            yield self_
    
    @classmethod
    def resend_all(self, denon):
        for self_ in self._get_features(denon):
            self_._send(denon)
            

class DenonFeature_Volume(DenonFeature):
    function = "MV"
    # TODO: value may be relative?
    # FIXME: on _poll MVMAX may be returned
    
    def __set__(self, denon, value):
        super(DenonFeature_Volume,self).__set__(denon, self._roundVolume(value))
        
    @staticmethod
    def _roundVolume(vol):
        return .5*round(vol/.5)

    def decodeVal(self, val):
        return int(val.ljust(3,"0"))/10
        
    def encodeVal(self, val):
        return "%03d"%(val*10)
        
        
class DenonFeature_Maxvol(DenonFeature_Volume):
    function="MVMAX "
    
    def _poll(self, denon):
        cmd = denon("MV?", ret=self.function)
        if cmd: return self._consume(denon, cmd)
        denon.__dict__[self_._name] = 98
        return denon.__dict__.get(self_._name)
        
    def encodeVal(self, val):
        raise RuntimeError("Cannot set MVMAX!")
        
    def _send(self, denon): pass
        

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
        self.connecting_lock = Lock()
        self.connected = False
        try: self.connect()
        except OSError: pass

    def _send(self, cmd):
        cmd = cmd.upper()
        try: self._telnet.write(("%s\n"%cmd).encode("ascii"))
        except (OSError, EOFError) as e:
            self.on_connection_lost()
            raise BrokenPipeError(e)
        return cmd
        
    def _read(self, timeout=None):
        try: return self._telnet.read_until(b"\r",timeout=timeout).strip().decode()
        except socket.timeout: return None
        except EOFError as e:
            self.on_connection_lost()
            raise BrokenPipeError(e)
        
    def __call__(self, cmd, ret=None):
        """ 
        Send command to AVR
        @cmd str: function[?|param]
        @ret str: return received line that starts with @ret, default: function
        """
        cmd = cmd.upper()
        if self.verbose: print("[Denon cli] %s"%cmd, file=sys.stderr)
        if "?" not in cmd and not ret: return self._send(cmd)

        ret = ret or cmd.replace("?","")
        def _return(r):
            if self.verbose: print(r, file=sys.stderr)
            return r
        condition = lambda r: r.startswith(ret)

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
                if not r:
                    if i>5: # timeout #TODO
                        sys.stderr.write("(timeout) ")
                        break
                    continue
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

    def connect(self, tries=1):
        """
        @tries int: -1 for infinite
        """
        while tries:
            if tries > 0: tries -= 1
            try: self._telnet = Telnet(self.host,23,timeout=2)
            except (ConnectionError, socket.timeout, socket.gaierror, socket.herror):
                if tries == 0: raise
            else:
                return self.on_connect()
            time.sleep(3)
    
    def on_connect(self):
        if self.verbose: print("[%s] connected to %s"%(self.__class__.__name__,self.host), file=sys.stderr)
        self.connected = True
        
    def on_connection_lost(self):
        print("[%s] connection lost"%self.__class__.__name__, file=sys.stderr)
        self.connected = False
        if not self.connecting_lock.acquire(blocking=False): return
        try: Thread(target=self.connect, args=(-1,), name="reconnecting", daemon=True).start()
        finally: self.connecting_lock.release()
        

class Denon(BasicDenon):
    """ Mapping of commands into python methods """

    maxvol = DenonFeature_Maxvol()
    volume = DenonFeature_Volume()
    muted = DenonFeature_Muted()
    is_running = DenonFeature_Power()
    
    def __init__(self, *args, **xargs):
        super(Denon,self).__init__(*args,**xargs)
        Thread(target=self.mainloop, name=self.__class__.__name__, daemon=True).start()

    def on_avr_change(self, attrib, new_val):
        pass
        
    def mainloop(self):
        while True:
            try:
                cmd = self.read()
            except ConnectionError: time.sleep(2)
            else:
                for attrib,f in self.features.items():
                    try: old, new = f._consume(self, cmd)
                    except ValueError: continue
                    else: 
                        if old != new: self.on_avr_change(attrib,new)

    def poweron(self,force=False): # TODO: check denon.source
        if not force and not config.getboolean("AVR","control_power_on") or self.is_running:
            return 0
        self.is_running = True
        time.sleep(3) #TODO
        return 1

    def poweroff(self, force=False):
        if not force and not config.getboolean("AVR","control_power_off"): return 0
        self.is_running = False
        return 1
        
    def resend_all(self):
        DenonFeature.resend_all(self)
    
    @property
    def features(self):
        return {f._name:f for f in DenonFeature._get_features(self)}


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

