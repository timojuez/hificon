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

    def __init__(self, denon, name):
        self.denon = denon

    def get(self):
        if not self.denon.connected: 
            raise ConnectionError("`%s` is not available when AVR is disconnected."%self.__class__.__name__)
        try: return self._val
        except AttributeError:
            self._poll()
            return self._val
        
    def set(self, value):
        if getattr(self, "_val", None) == value: return
        self._val = value
        self._send()

    def _isset(self):
        return hasattr(self,'_val')
        
    def _poll(self):
        return self._consume(self.denon("%s?"%self.function))
    
    def _send(self):
        cmd = "%s%s"%(self.function, self.encodeVal(self._val))
        self.denon(cmd)
    
    def _consume(self, cmd):
        """
        Update property according to @cmd
        """
        if not cmd.startswith(self.function): 
            raise ValueError("Cannot handle `%s`."%cmd)
        param = cmd[len(self.function):]
        old = getattr(self,'_val',None)
        self._val = self.decodeVal(param)
        return old, self._val
    

class DenonFeature_Volume(DenonFeature):
    function = "MV"
    # TODO: value may be relative?
    # FIXME: on _poll MVMAX may be returned
    
    def set(self, value):
        super(DenonFeature_Volume,self).set(self._roundVolume(value))
        
    @staticmethod
    def _roundVolume(vol):
        return .5*round(vol/.5)

    def decodeVal(self, val):
        return int(val.ljust(3,"0"))/10
        
    def encodeVal(self, val):
        return "%03d"%(val*10)
        
        
class DenonFeature_Maxvol(DenonFeature_Volume):
    function="MVMAX "
    
    def _poll(self):
        cmd = self.denon("MV?", ret=self.function)
        if cmd: return self._consume(cmd)
        old = getattr(self,'_val',None)
        self._val = 98
        return old, self._val
        
    def encodeVal(self, val):
        raise RuntimeError("Cannot set MVMAX!")
        
    def _send(self): pass
        

class DenonFeature_Power(DenonFeature):
    function = "PW"
    translation = {"ON":True,"STANDBY":False}
    
    
class DenonFeature_Muted(DenonFeature):
    function = "MU"
    translation = {"ON":True,"OFF":False}



class DenonWithFeatures(object):
    maxvol = DenonFeature_Maxvol
    volume = DenonFeature_Volume
    muted = DenonFeature_Muted
    is_running = DenonFeature_Power
    
    features = {}
    
    def __init__(self):
        for name, Feature in self.__class__.__dict__.items():
            if issubclass(Feature,DenonFeature):
                f = Feature(self, name)
                self.__dict__[name] = property(f.get, f.set)
                self.features[name] = f
                


class BasicDenon(object):
    """
    This class connects to the Denon AVR via LAN and executes commands (see Denon CLI protocol)
    @host is the AVR's hostname or IP.
    """

    def __init__(self, host=None, verbose=False):
        super(BasicDenon).__init__()
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
        

class Denon(BasicDenon,DenonWithFeatures):
    """ Mapping of commands into python methods """

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
                except (KeyboardInterrupt, EOFError): break
                cmd = denon._send(cmd)
                #print("\r[sent] %s"%cmd)
            

main = lambda:CLI()()
if __name__ == "__main__":
    main()

