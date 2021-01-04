"""
Common amplifier classes for creating an amp protocol.
Use TelnetAmp or AbstractAmp. Examples in ./protocol
"""

import sys, time, socket
from threading import Timer, Lock, Thread, Event
from telnetlib import Telnet
from contextlib import suppress
from .amp_type import AmpType
from .features import *
from ..util.function_bind import Bindable
from ..util import log_call, AttrDict
from ..common.config import config
from ..common.config import FILE as CONFFILE
from .. import NAME


class _AbstractAmp(Bindable, AmpType):
    """
    Abstract Amplifier Interface
    Note: Event callbacks (on_connect, on_feature_change) might be called in the mainloop
        and delay further command processing. Use threads for not blocking the
        mainloop.
    """
    
    protocol = None
    host = None
    port = None
    connected = False
    verbose = 0
    _mainloopt = None
    _stoploop = None
    _connectOnEnter = False

    def __init__(self, host=None, port=None, connect=True, verbose=0, **callbacks):
        super().__init__()
        self._stoploop = Event()
        self._connectOnEnter = connect
        self.verbose = verbose
        self.bind(**callbacks)
        self.host = host or self.host or config["Amp"].get("Host")
        self.port = port or self.port or config["Amp"].getint("port")
        if not self.host: raise RuntimeError("Host is not set! Execute setup or set AVR "
            "IP or hostname in %s."%CONFFILE)
        if config.power in self.features: self.features[config.power].bind(
            on_change = lambda _,val:self.on_poweron() if val else self.on_poweroff())
    
    def __enter__(self): return self.enter()

    def __exit__(self, type, value, tb): self.exit()

    def enter(self):
        if self._connectOnEnter: self.connect()
        self._stoploop.clear()
        self._mainloopt = Thread(target=self.mainloop, name=self.__class__.__name__, daemon=True)
        self._mainloopt.start()
        return self

    def exit(self): self.disconnect(); self._mainloopt.join()
    
    def connect(self): self.connected = True

    def disconnect(self): self._stoploop.set()
    
    @classmethod
    def get_protocol(self): return self.protocol or self.__module__

    @property
    def prompt(self):
        p = "%s://%s"%(self.get_protocol(),self.host)
        if self.port: p = "%s:%s"%(p,self.port)
        return p
        
    def query(self, cmd, matches=None):
        """
        Low level function that sends @cmd and returns a value where matches(value) is True.
        Only called by hifish
        """
        raise NotImplementedError()

    __call__ = lambda self,*args,**xargs: self.query(*args,**xargs)
        
    def send(self, cmd):
        if self.verbose > 4: print("%s $ %s"%(self.prompt, cmd), file=sys.stderr)

    @log_call
    def on_connect(self):
        """ Execute when connected to amp e.g. after connection aborted """
        if self.verbose > 0:
            print("[%s] connected to %s"%(self.__class__.__name__, self.prompt), file=sys.stderr)
        
    @log_call
    def on_disconnected(self): self.connected = False

    @log_call
    def on_feature_change(self, key, value, previous_val):
        """ attribute on amplifier has changed """
        if key and self.verbose > 2:
            print("[%s] $%s = %s"%(self.__class__.__name__,key,repr(value)))
        
    @log_call
    def on_poweron(self): pass
    
    @log_call
    def on_poweroff(self): pass

    def on_receive_raw_data(self, data):
        if self.verbose > 4: print(data, file=sys.stderr)

    def mainloop(self):
        """ listens on amp for events and calls on_feature_change. Return when connection closed """
        while not self._stoploop.is_set(): self.mainloop_hook()
        
    def mainloop_hook(self):
        """ This will be called regularly by mainloop """
        pass
    
    
class SoundMixin:
    """ provide on_start_playing, on_stop_playing, on_idle """
    _soundMixinLock = Lock()
    _idle_timer = None

    @log_call
    def on_start_playing(self):
        if self._idle_timer: self._idle_timer.cancel()

    @log_call
    def on_stop_playing(self):
        with self._soundMixinLock:
            if self._idle_timer and self._idle_timer.is_alive(): return
            try: timeout = config.getfloat("Amp","poweroff_after")*60
            except ValueError: return
            if not timeout: return
            self._idle_timer = Timer(timeout, self.on_idle)
            self._idle_timer.start()
    
    @log_call
    def on_idle(self): pass

    def on_poweroff(self):
        super().on_poweroff()
        if self._idle_timer: self._idle_timer.cancel()


class FeaturesMixin(object):
    features = {}
    _pending = list
    _polled = list

    def __init__(self,*args,**xargs):
        self._pending = self._pending()
        self._polled = self._polled()
        self.features = AttrDict()
        def disable_add_feature(*args, **xargs): raise TypeError("add_feature must be called on class.")
        self.add_feature = disable_add_feature
        # apply @features to Amp
        for F in self.__class__.features.values(): F(self)
        super().__init__(*args,**xargs)

    @classmethod
    def add_feature(cls, Feature=None, overwrite=False):
        """
        This is a decorator to be used on Feature class definitions that belong to the current amp.
        @overwrite: If true, proceeds if a feature with same key already exists.
        Example:
            from amp.feature import Feature
            @Amp.add_feature
            class MyFeature(Feature): pass
        """
        def add(Feature, overwrite=overwrite):
            if hasattr(cls.features.__class__, Feature.key):
                raise KeyError("Feature.key `%s` is already occupied."%Feature.key)
            if not overwrite and hasattr(cls, Feature.key):
                raise KeyError(
                    "Feature.key `%s` is already occupied. Use add_feature(overwrite=True)"%Feature.key)
            setattr(cls, Feature.key, property(
                lambda self:self.features[Feature.key].get(),
                lambda self,val:self.features[Feature.key].set(val)
            ))
            cls.features = {**cls.features, Feature.key: Feature}
            return Feature
        return add(Feature) if Feature else add
    
    def __setattr__(self, name, value):
        """ @name must match an existing attribute """
        if hasattr(self.__class__, name): super().__setattr__(name, value)
        else:
            raise AttributeError(("%s object has no attribute %s. To rely on optional features, "
                "use decorator @amp.features.require('attribute')")%(repr(self.__class__.__name__),repr(name)))

    def on_disconnected(self):
        super().on_disconnected()
        self._pending.clear()
        self._polled.clear()
        for f in self.features.values(): f.unset()
    
    def mainloop_hook(self):
        super().mainloop_hook()
        for p in self._pending: p.check_expiration()
    
    def on_receive_raw_data(self, data):
        super().on_receive_raw_data(data)
        for line in data.split("\n"):
            consumed = [f.consume(line) for key,f in self.features.items() if f.matches(line)]
            if not consumed: self.features.fallback.consume(line)


class PreloadMixin:
    preload_features = set() # feature keys to be polled on_connect

    def on_connect(self):
        super().on_connect()
        for key in set(self.preload_features):
            if key in self.features: self.features[key].async_poll()


class AbstractAmp(PreloadMixin, FeaturesMixin, SoundMixin, _AbstractAmp): pass

    
class TelnetAmp(AbstractAmp):
    """
    This class connects to the amp via LAN and executes commands
    @host is the amp's hostname or IP.
    """
    pulse = ""
    _telnet = None
    _send_lock = None
    _pulse_stop = None
    
    def __init__(self, *args, **xargs):
        super().__init__(*args, **xargs)
        self._send_lock = Lock()
        self._pulse_stop = Event()

    def send(self, cmd):
        super().send(cmd)
        try:
            with self._send_lock:
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
    
    def connect(self):
        if self.connected: return
        try: self._telnet = Telnet(self.host,self.port,timeout=2)
        except (ConnectionError, socket.timeout, socket.gaierror, socket.herror, OSError) as e:
            raise ConnectionError(e)
        else:
            super().connect()
            return self.on_connect()

    def disconnect(self):
        super().disconnect()
        self._pulse_stop.set()
        with suppress(AttributeError, OSError):
            self._telnet.sock.shutdown(socket.SHUT_WR) # break read()
            self._telnet.close()
    
    def on_connect(self):
        super().on_connect()
        def func():
            while not self._pulse_stop.wait(10): self.send(self.pulse)
        self._pulse_stop.clear()
        if self.pulse is not None: Thread(target=func, daemon=True, name="pulse").start()
        
    def on_disconnected(self):
        super().on_disconnected()
        self._pulse_stop.set()
        
    def mainloop_hook(self):
        super().mainloop_hook()
        if self.connected:
            try: data = self.read(5)
            except ConnectionError: pass
            else:
                if data: self.on_receive_raw_data(data)
        else:
            try: self.connect()
            except ConnectionError: return self._stoploop.wait(3)


@AbstractAmp.add_feature
class Fallback(SelectFeature):
    """ Matches always, if no other feature matched """
    
    def matches(self, data): return False
    def set(self, *args, **xargs): raise ValueError("Cannot set value!")
    def async_poll(self, *args, **xargs): pass
    def isset(self): return super().isset() and config.getboolean("Amp","fallback_feature")

    def consume(self, data):
        self._val = data
        if self.amp.verbose > 1:
            print("[%s] WARNING: could not parse `%s`"%(self.__class__.__name__, data))
        if config.getboolean("Amp","fallback_feature"): self.on_change(None, data)


@AbstractAmp.add_feature
class Name(SelectFeature):
    
    def get(self): return self.amp.prompt
    def matches(self, data): return False
    def set(self, *args, **xargs): raise ValueError("Cannot set value!")
    def async_poll(self, *args, **xargs): pass
    def isset(self): return True
    def unset(self): pass

