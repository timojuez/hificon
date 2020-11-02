"""
Common amplifier classes for creating an amp protocol.
Use TelnetAmp or AbstractAmp. Examples in ./protocol
"""

import sys, time, socket
from threading import Thread
from telnetlib import Telnet
from contextlib import suppress
from .amp_type import AmpType
from .features import require
from ..util.function_bind import Bindable
from ..util import log_call
from ..config import config
from ..config import FILE as CONFFILE
from .. import NAME


class _AbstractAmp(Bindable, AmpType):
    """
    Abstract Amplifier Interface
    Note: Event callbacks (on_connect, on_change) might be called in the mainloop
        and delay further command processing. Use threads for not blocking the
        mainloop.
    """
    
    protocol = None
    host = None
    port = None
    name = None
    connected = False
    verbose = 0
    _mainloopt = None
    _stoploop = None

    def __init__(self, host=None, port=None, name=None, verbose=0, **callbacks):
        super().__init__()
        self.verbose = verbose
        self.bind(**callbacks)
        self.host = host or self.host or config["Amp"].get("Host")
        self.port = port or self.port or config["Amp"].getint("port")
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
    
    @property
    def prompt(self):
        p = "%s://%s"%(self.protocol,self.host)
        if self.port: p = "%s:%d"%(p,self.port)
        return p
        
    def query(self, cmd, matches=None):
        """
        Low level function that sends @cmd and returns a value where matches(value) is True.
        Only called by hifish
        """
        raise NotImplementedError()

    __call__ = lambda self,*args,**xargs: self.query(*args,**xargs)
        
    def send(self, cmd): raise NotImplementedError()

    @require("power","source")
    def poweron(self, force=False):
        if not force and not config.getboolean("Amp","control_power_on") or self.power:
            return
        if config["Amp"].get("source"): self.features["source"].set(config["Amp"]["source"], force=True)
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
    def on_change(self, attr, new_val):
        """ attribute on amplifier has changed """
        if attr == None and self.verbose > 1:
            print("[%s] WARNING: could not parse `%s`"%(self.__class__.__name__, new_val))
        elif attr and self.verbose > 2:
            print("[%s] $%s = %s"%(self.__class__.__name__,attr,repr(new_val)))
        
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
        pass
    
    
class FeaturesMixin(object):
    features = {}
    _pending = None
    _polled = []

    def __init__(self,*args,**xargs):
        self._pending = []
        self.features = {}
        # apply @features to Amp
        for attr,F in self._feature_classes.items(): F(self,attr)
        super().__init__(*args,**xargs)

    def __setattr__(self, name, value):
        """ @name must match an existing attribute """
        if not hasattr(self, name):
            raise AttributeError(("%s object has no attribute %s. To rely on optional features, "
                "use decorator @amp_features.require('attribute')")%(repr(self.__class__.__name__),repr(name)))
        else: super().__setattr__(name, value)

    def on_connect(self):
        self._polled.clear()
        for f in self.features.values(): f.unset()
        super().on_connect()
    
    def _set_feature_value(self, name, value):
        self.features[name].set(value)
    
    def mainloop_hook(self):
        super().mainloop_hook()
        for p in self._pending: p.check_expiration()
    
    def on_receive_raw_data(self, data):
        super().on_receive_raw_data(data)
        consumed = {attrib:f.consume(data) for attrib,f in self.features.items() if f.matches(data)}
        consumed = {attrib:values for attrib,values in consumed.items() if values}
        if not consumed: self.on_change(None, data)
        for attr,(old,new) in consumed.items():
            if self.verbose > 5 and self._pending: print("[%s] %d pending functions"
                %(self.__class__.__name__, len(self._pending)), file=sys.stderr)
            if attr in self.features and not self.features[attr].isset(): continue
            if (not any([p.has_polled(attr) for p in self._pending.copy()]) # has_polled() changes self._pending
                    and old != new):
                self.on_change(attr, new)


class PreloadMixin:
    preload_features = set() # feature keys to be polled on_connect

    def on_connect(self):
        super().on_connect()
        def preload(amp): pass
        for f in set(self.preload_features): f not in self.features or require(f)(preload)(self)
        

class SendOnceMixin(object): # TODO: move to Feature so that it affects f.set()
    """ prevent the same values from being sent to the amp in a row """
    _block_on_set = None
    
    def __init__(self,*args,**xargs):
        self._block_on_set = {}
        super().__init__(*args,**xargs)
        
    def _set_feature_value(self, name, value):
        if name in self._block_on_set and self._block_on_set[name] == value:
            return
        self._block_on_set[name] = value
        super()._set_feature_value(name,value)
        
    def on_change(self,*args,**xargs):
        self._block_on_set.clear() # unblock values after amp switches on
        super().on_change(*args,**xargs)


class AbstractAmp(SendOnceMixin, PreloadMixin, FeaturesMixin, _AbstractAmp): pass

    
class TelnetAmp(AbstractAmp):
    """
    This class connects to the amp via LAN and executes commands
    @host is the amp's hostname or IP.
    """
    _telnet = None
    
    def send(self, cmd):
        if self.verbose > 4: print("%s $ %s"%(self.prompt, cmd), file=sys.stderr)
        try:
            assert(self.connected and self._telnet.sock)
            self._telnet.write(("%s\r"%cmd).encode("ascii"))
            time.sleep(.01)
        except (OSError, EOFError, AssertionError, AttributeError) as e:
            self.on_disconnected()
            raise BrokenPipeError(e)
        
    def read(self, timeout=None):
        try:
            assert(self.connected and self._telnet.sock)
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
            try: self._telnet = Telnet(self.host,self.port,timeout=2)
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
        super().mainloop_hook()
        if not self.connected: self.connect(-1)
        try: data = self.read(5)
        except ConnectionError: pass
        else:
            # receiving
            if not data: return
            if self.verbose > 4: print(data, file=sys.stderr)
            self.on_receive_raw_data(data) 


def make_amp(features, base_cls=AbstractAmp):
    """
    Make a class where all attributes are getters and setters for amp properties
    features: dict(class_attribute_name=MyFeature)
        where MyFeature inherits from amp_features.Feature
    """
    assert(issubclass(base_cls, AmpType))
    for name in features.keys(): 
        if hasattr(base_cls,name):
            raise KeyError("Key `%s` is ambiguous and may not be used as a feature."%name)

    dict_ = {
        k:property(
            lambda self,k=k:self.features[k].get(),
            lambda self,val,k=k:self._set_feature_value(k,val)
        )
        for k,v in features.items()
    }
    dict_["_feature_classes"] = features

    with suppress(Exception): dict_["protocol"] = \
        base_cls.protocol or sys._getframe(1).f_globals['__name__']
    return type("Amp", (base_cls,), dict_)
    
