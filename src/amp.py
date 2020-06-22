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
from .amp_features import Feature, make_feature
from . import NAME


def require(*features):
    """
    Decorator that states which amp features have to be loaded before calling the function.
    Call might be delayed until the feature values have been set.
    Can be used in types AbstractAmp or AmpEvents.
    Example: @require("volume","muted")
    """
    def _find_amp(args): 
        """ search AbstractAmp type in args """
        try:
            amp = getattr(args[0],"amp",None)
            return next(filter(lambda e: isinstance(e,AbstractAmp), (amp,)+args))
        except (StopIteration, IndexError):
            raise Exception("@require needs AbstractAmp instance")
    
    def decorator(func):
        def call(*args,**xargs):
            amp = _find_amp(args)
            try:
                assert(amp.connected and hasattr(amp,"features"))
                features_ = [amp.features[name] for name in features]
            except (AssertionError, AttributeError, KeyError): return
            unset = list(filter(lambda f:not f.isset(), features_))
            if unset:
                try: [f.poll() for f in unset]
                except ConnectionError: return
                #return amp._pending.append((datetime(),unset,func,args,xargs))
            return func(*args,**xargs)
        return call
    return decorator


class AbstractAmp(Bindable):
    """
    Abstract Amplifier Interface
    Note: Event callbacks (on_connect, on_change) might be called in the mainloop
        and delay further command processing. Use threads for not blocking the
        mainloop.
    """
    
    protocol = "Undefined"
    host = "Undefined"
    name = None
    features = {}
    connected = False

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

    def disconnect(self): pass
        
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

    def mainloop(self):
        """ listens on amp for events and calls on_change. Return when connection closed """
        raise NotImplementedError()
    

class TelnetAmp(AbstractAmp):
    """
    This class connects to the amp via LAN and executes commands
    @host is the amp's hostname or IP.
    """

    def send(self, cmd):
        if self.verbose > 3: print("%s@%s:%s $ %s"%(NAME,self.host,self.protocol,cmd), file=sys.stderr)
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
    
    def query(self, cmd, matches=None):
        """
        send @cmd to amp and return line where matches(line) is True
        """
        if not matches: return self.send(cmd)
        else: return make_feature(self,cmd,matches).get()
    
    __call__ = lambda self,*args,**xargs: self.query(*args,**xargs)
    
    def connect(self, tries=1):
        """
        @tries int: -1 for infinite
        """
        if self.connected: return
        while tries:
            if tries > 0: tries -= 1
            try: self._telnet = Telnet(self.host,23,timeout=2)
            except (ConnectionError, socket.timeout, socket.gaierror, socket.herror, OSError):
                if tries == 0: raise
            else:
                super().connect()
                return Thread(name="on_connect",target=self.on_connect).start()
            time.sleep(3)

    def disconnect(self):
        #super().disconnect()
        self._stoploop = True
        with suppress(AttributeError):
            self._telnet.sock.shutdown(socket.SHUT_WR) # break read()
            self._telnet.close()

    def on_receive_raw_data(self, data): pass

    def mainloop(self):
        self._stoploop = False
        while not self._stoploop:
            try: cmd = self.read(5)
            except ConnectionError: 
                if not self._stoploop: self.connect(-1)
            else:
                # receiving
                if  not cmd: continue
                self.on_receive_raw_data(cmd) # TODO: instead use minimalistic protocol.raw_telnet and listen on on_change(None, cmd)
                if self.verbose > 3: print(cmd, file=sys.stderr)
                consumed = {attrib:f.consume(cmd) for attrib,f in self.features.items() if f.matches(cmd)}
                if not consumed: Thread(name="on_change",target=self.on_change,args=(None, cmd)).start()
                elif False in consumed.values(): continue
                for attrib,(old,new) in consumed.items():
                    if old != new: Thread(name="on_change",target=self.on_change,args=(attrib,new)).start()


def _make_features_mixin(**features):
    """
    Make a class where all attributes are getters and setters for amp properties
    args: class_attribute_name=MyFeature
        where MyFeature inherits from Feature
    """
    
    class FeatureMixin(object):
        """ apply @features to Amp """

        def __init__(self,*args,**xargs):
            self.features = {}
            for k,v in features.items(): v(self,k)
            super().__init__(*args,**xargs)
        
        def on_connect(self):
            for f in self.features.values(): f.unset()
            super().on_connect()
        
        def _set_feature_value(self, name, value):
            self.features[name].set(value)
        

    class SendOnceMixin(object):
        """ prevent the same values from being sent to the amp in a row """

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
        
        
    dict_ = dict()
    try: dict_["protocol"] = sys._getframe(2).f_globals['__name__']
    except: pass
    dict_.update({
        k:property(
            lambda self,k=k:self.features[k].get(),
            lambda self,val,k=k:self._set_feature_value(k,val)
        )
        for k,v in features.items()
    })
    cls = type("AmpFeatures", (SendOnceMixin,FeatureMixin), dict_)
    return cls


def make_amp(features, base_cls=object):
    for name in features.keys(): 
        if hasattr(base_cls,name):
            raise KeyError("Key `%s` is ambiguous and may not be used as a feature."%name)
    return type("Amp", (_make_features_mixin(**features),base_cls), dict())
    
