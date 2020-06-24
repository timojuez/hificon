"""
Common amplifier classes for creating an amp protocol.
Use TelnetAmp/AbstractAmp, Feature and make_amp(). Examples in ./protocol
"""

import sys, time, socket
from threading import Thread
from telnetlib import Telnet
from contextlib import suppress
from .util.function_bind import Bindable
from .util import log_call
from .config import config
from .config import FILE as CONFFILE
from .amp_features import Feature, require, make_features_mixin
from . import NAME


class AbstractAmp(Bindable):
    """
    Abstract Amplifier Interface
    Note: Event callbacks (on_connect, on_change) might be called in the mainloop
        and delay further command processing. Use threads for not blocking the
        mainloop.
    """
    
    protocol = None
    host = "Undefined"
    name = None
    features = {}
    connected = False

    prompt = property(lambda self: "%s:%s@%s"%(self.protocol,NAME,self.host))

    def __init__(self, host=None, name=None, verbose=0, **callbacks):
        super().__init__()
        self.verbose = verbose
        self.bind(**callbacks)
        self.host = host or config["Amp"].get("Host")
        self.name = name or self.name or config["Amp"].get("Name") or self.host
        if not self.host: raise RuntimeError("Host is not set! Install autosetup or set AVR "
            "IP or hostname in %s."%CONFFILE)
    
    def __enter__(self): self.connect(); self.enter(); return self

    def __exit__(self, type, value, tb): self.exit()

    def enter(self):
        self._mainloopt = Thread(target=self.mainloop, name=self.__class__.__name__, daemon=True)
        self._mainloopt.start()

    def exit(self): self.disconnect(); self._mainloopt.join()
    
    def connect(self, tries=1): self.connected = True

    def disconnect(self): self._stoploop = True
    
    def query(self, cmd, matches=None): raise NotImplementedError()

    __call__ = lambda self,*args,**xargs: self.query(*args,**xargs)
        
    @require("power","source")
    def poweron(self, force=False):
        if not force and not config.getboolean("Amp","control_power_on") or self.power:
            return
        if config["Amp"].get("source"): self.source = config["Amp"]["source"]
        self.power = True

    @require("power","source")
    def poweroff(self, force=False):
        if not force and (not config.getboolean("Amp","control_power_off") 
            or config["Amp"].get("source") and self.source != config["Amp"]["source"]): return
        self.power = False

    @log_call
    def on_connect(self):
        """ Execute when connected to amp e.g. after connection aborted """
        if self.verbose > 0: print("[%s] connected to %s"%(self.__class__.__name__,self.host), file=sys.stderr)
        
    @log_call
    def on_disconnected(self): self.connected = False

    @log_call
    def on_change(self, attrib, new_val):
        """ attribute on amplifier has changed """
        pass
        
    @log_call
    def on_poweron(self): pass
    
    @log_call
    def on_poweroff(self): pass

    def on_receive_raw_data(self, data): pass

    def mainloop(self):
        """ listens on amp for events and calls on_change. Return when connection closed """
        self._stoploop = False
        while not self._stoploop: self.mainloop_hook()
        
    def mainloop_hook(self):
        """ This will be called regularly by mainloop """
        raise NotImplementedError()
    

class TelnetAmp(AbstractAmp):
    """
    This class connects to the amp via LAN and executes commands
    @host is the amp's hostname or IP.
    """
    PORT = 23
    prompt = property(lambda self: "%s:%s"%(super().prompt,self.PORT))
    
    def send(self, cmd):
        if self.verbose > 3: print("%s $ %s"%(self.prompt, cmd), file=sys.stderr)
        try:
            assert(self.connected)
            self._telnet.write(("%s\n"%cmd).encode("ascii"))
        except (OSError, EOFError, AssertionError, AttributeError) as e:
            self.on_disconnected()
            raise BrokenPipeError(e)
        
    def read(self, timeout=None):
        try:
            assert(self.connected)
            return self._telnet.read_until(b"\r",timeout=timeout).strip().decode()
        except socket.timeout: return None
        except (OSError, EOFError, AssertionError, AttributeError) as e:
            self.on_disconnected()
            raise BrokenPipeError(e)
    
    def connect(self, tries=1):
        """
        @tries int: -1 for infinite
        """
        if self.connected: return
        while tries:
            if tries > 0: tries -= 1
            try: self._telnet = Telnet(self.host,self.PORT,timeout=2)
            except (ConnectionError, socket.timeout, socket.gaierror, socket.herror, OSError):
                if tries == 0: raise
            else:
                super().connect()
                return self.on_connect()
            time.sleep(3)

    def disconnect(self):
        super().disconnect()
        with suppress(AttributeError):
            self._telnet.sock.shutdown(socket.SHUT_WR) # break read()
            self._telnet.close()

    def mainloop_hook(self):
        if not self.connected: self.connect(-1)
        try: data = self.read(5)
        except ConnectionError: pass
        else:
            # receiving
            if not data: return
            if self.verbose > 3: print(data, file=sys.stderr)
            self.on_receive_raw_data(data) 


def make_amp(features, base_cls=AbstractAmp):
    assert(issubclass(base_cls, AbstractAmp))
    for name in features.keys(): 
        if hasattr(base_cls,name):
            raise KeyError("Key `%s` is ambiguous and may not be used as a feature."%name)
    dict_ = dict()
    with suppress(Exception): dict_["protocol"] = \
        base_cls.protocol or sys._getframe(1).f_globals['__name__']
    return type("Amp", (make_features_mixin(**features),base_cls), dict_)
    
