#!/usr/bin/env python3
# -*- coding: utf-8 -*- 

import sys, time, argparse, socket
from threading import Lock, Thread
from telnetlib import Telnet
from .config import config
from .config import FILE as CONFFILE
from .amp_features import DenonWithFeatures
try: from .setup import DenonDiscoverer
except ImportError: pass


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
        #try: self.connect()
        #except OSError: pass
        self.connect_async()

    def _send(self, cmd):
        cmd = cmd.upper()
        try:
            assert(self.connected)
            self._telnet.write(("%s\n"%cmd).encode("ascii"))
        except (OSError, EOFError, AssertionError) as e:
            self.on_connection_lost()
            raise BrokenPipeError(e)
        return cmd
        
    def _read(self, timeout=None):
        try:
            assert(self.connected)
            return self._telnet.read_until(b"\r",timeout=timeout).strip().decode()
        except socket.timeout: return None
        except (EOFError, AssertionError) as e:
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

        def _return(r):
            if self.verbose: print(r, file=sys.stderr)
            return r
        ret = ret or cmd.replace("?","")
        condition = ret if callable(ret) else lambda r: r.startswith(ret)

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
        self.connecting_lock.acquire() #blocking=False
        try:
            if self.connected: return
            while tries:
                if tries > 0: tries -= 1
                try: self._telnet = Telnet(self.host,23,timeout=2)
                except (ConnectionError, socket.timeout, socket.gaierror, socket.herror):
                    if tries == 0: raise
                else:
                    return self.on_connect()
                time.sleep(3)
        finally: self.connecting_lock.release()
    
    def connect_async(self):
        Thread(target=self.connect, args=(-1,), name="connecting", daemon=True).start()
        
    def on_connect(self):
        if self.verbose: print("[%s] connected to %s"%(self.__class__.__name__,self.host), file=sys.stderr)
        self.connected = True
        
    def on_connection_lost(self):
        print("[%s] connection lost"%self.__class__.__name__, file=sys.stderr)
        self.connected = False
        self.connect_async()
    

class AsyncDenon(BasicDenon, metaclass=DenonWithFeatures):
    """ Mapping of commands into python methods """

    def __init__(self, *args, **xargs):
        super().__init__(*args,**xargs)
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
                    try: old, new = f._consume(cmd)
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
        

def call_sequence(*functions):
    return lambda *args,**xargs: [f(*args,**xargs) for f in functions]


class DenonWithEvents(AsyncDenon,EventHandler):
    """
    Event handler that keeps up to date the plugin data such as the volume
    and controls the AVR's power state.
    """
    
    def __init__(self, verbose=False, **callbacks):
        self.denon = self
        for name, callback in callbacks.items():
            setattr(self, name, call_sequence(getattr(self,name), callback))
        Denon.__init__(self,verbose=verbose)
        _EventHandler.__init__(self)

    def loop(self):
        try:
            while True: time.sleep(1000)
        except KeyboardInterrupt: pass
    
    @property
    def update_actions(self):
        return {
            "is_running": 
                lambda value:{True:self.on_avr_poweron, False:self.on_avr_poweroff}[value](),
        }

    def on_shutdown(self, sig, frame):
        """ when shutting down computer """
        try: self.denon.poweroff()
        except ConnectionError: pass
        
    def on_suspend(self):
        try: self.denon.poweroff()
        except ConnectionError: pass
    
    def on_resume(self):
        """ Is being executed after resume from suspension """
        self.on_connection_lost()
        
    def on_connect(self):
        """ Execute when connected e.g. after connection aborted """
        super(EventHandler,self).on_connect()
        try: 
            #self.denon.poll_all() # TODO: better asynchronous and return
            self.denon.features["is_running"]._poll()
            for attr, f in self.denon.features.items():
                    if not f._isset() or self.denon.is_running: 
                        old, new = f._poll()
                        if old != new: self.on_avr_change(attr,new)
        except ConnectionError: pass
            
    def on_connection_lost(self):
        super(EventHandler,self).on_connection_lost()
        
    def on_avr_poweron(self):
        pass
        
    def on_avr_poweroff(self):
        pass

    def on_avr_change(self, attrib, value):
        super(EventHandler,self).on_avr_change(attrib, value)
        func = self.update_actions.get(attrib)
        if func: func(value)


def echo_call(name, func):
    def call(self,*args,**xargs):
        print("[%s] %s"%(self.__class__.__name__,name), file=sys.stderr) 
        return func(self,*args,**xargs)
    return call
for k in dir(DenonWithEvents):
    if k.startswith("on_"): setattr(DenonWithEvents,k,echo_call(k,getattr(DenonWithEvents,k)))


Denon=DenonWithEvents


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
        denon.connect()
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

