"""
The classes AbstractClient and TelnetClient help you to stay synchronised with
values from a Telnet or non-Telnet server. A client supports features. See features.py.
"""

import sys
from threading import Thread, Event
from ..util.function_bind import Bindable
from ..util import log_call
from ..config import config
from ..config import FILE as CONFFILE
from .protocol_type import ProtocolType
from . import features


class ProtocolBase(Bindable, ProtocolType):
    protocol = None
    verbose = 0
    connected = False
    features = features.Features()
    _pending = list

    def __init__(self, *args, verbose=0, **xargs):
        self.verbose = verbose
        self.features = self.features.__class__()
        self._pending = self._pending()
        def disable_add_feature(*args, **xargs): raise TypeError("add_feature must be called on class.")
        self.add_feature = disable_add_feature
        # apply @features to Amp
        for F in self.__class__.features.values(): F(self)
        super().__init__(*args, **xargs)

    def __setattr__(self, name, value):
        """ @name must match an existing attribute """
        if hasattr(self.__class__, name): super().__setattr__(name, value)
        else: raise AttributeError(("%s object has no attribute %s. To rely on "
            "optional features, use Target.schedule.")
            %(repr(self.__class__.__name__),repr(name)))

    def _setfattr(self, key, value):
        """ This is being called by setattr(self, f, value) if getattr(self, f) is a Feature type """
        raise NotImplementedError()
        
    def __enter__(self): self.enter(); return self

    def __exit__(self, type, value, tb): self.exit()

    def enter(self): pass
    
    def exit(self): pass
    
    @classmethod
    def get_protocol(self): return self.protocol or self.__module__

    @property
    def prompt(self): return self.get_protocol()
        
    @classmethod
    def add_feature(cls, Feature=None, overwrite=False):
        """
        This is a decorator to be used on Feature class definitions that belong to the current class.
        @overwrite: If true, proceeds if a feature with same key already exists.
        Example:
            from client.feature import Feature
            @AbstractClient.add_feature
            class MyFeature(Feature): pass
        """
        def add(Feature, overwrite=overwrite):
            if not issubclass(Feature, features.Feature):
                raise TypeError(f"Feature must be of type {features.Feature}")
            if Feature.key.startswith("_"): raise KeyError("Feature.key may not start with '_'")
            if hasattr(cls.features.__class__, Feature.key):
                raise KeyError("Feature.key `%s` is already occupied."%Feature.key)
            if not overwrite and hasattr(cls, Feature.key):
                raise KeyError(
                    "Feature.key `%s` is already occupied. Use add_feature(overwrite=True)"%Feature.key)
            setattr(cls, Feature.key, property(
                lambda self:self.features[Feature.key].get(),
                lambda self,val:self._setfattr(Feature.key, val)
            ))
            cls.features = cls.features.__class__({**cls.features, Feature.key: Feature})
            return Feature
        return add(Feature) if Feature else add
    
    def poll_feature(self, f, *args, **xargs): raise NotImplementedError()

    def schedule(self, func, args=tuple(), xargs={}, requires=tuple()):
        @features.require(*requires)
        def f(target): return func(*args, **xargs)
        return f(self)
    
    @log_call
    def on_feature_change(self, key, value, previous_val):
        """ attribute on server has changed """
        if key and self.verbose > 2:
            print("[%s] $%s = %s"%(self.__class__.__name__,key,repr(value)))
        
    def send(self, data): raise NotImplementedError()

    def on_receive_raw_data(self, data):
        if self.verbose > 4: print(data, file=sys.stderr)
        consumed = [f.consume(data) for key,f in self.features.items() if f.matches(data)]
        if not consumed: self.features.fallback.consume(data)


@ProtocolBase.add_feature
class Fallback(features.SelectFeature):
    """ Matches always, if no other feature matched """
    
    def matches(self, data): return False
    def send(self, *args, **xargs): raise ValueError("Cannot set value!")
    def resend(self, *args, **xargs): pass
    def async_poll(self, *args, **xargs): pass
    def isset(self): return super().isset() and config.getboolean("Target","fallback_feature")

    def consume(self, data):
        self._val = data
        if self.amp.verbose > 1:
            print("[%s] WARNING: could not parse `%s`"%(self.__class__.__name__, data))
        if config.getboolean("Target","fallback_feature"): self.on_change(None, data)


@ProtocolBase.add_feature
class Name(features.SelectFeature):
    
    def get(self): return self.amp.prompt
    def matches(self, data): return False
    def send(self, *args, **xargs): raise ValueError("Cannot set value!")
    def async_poll(self, *args, **xargs): pass
    def isset(self): return True
    def unset(self): pass
    def resend(self, *args, **xargs): pass


class AbstractServer(ProtocolBase):

    def __init__(self, *args, **xargs):
        super().__init__(*args, **xargs)
        for f in self.features.values(): not f.key=="fallback" and f.bind(on_store=lambda *_,f=f:f.resend())
    
    def enter(self): self.connected = True
    def exit(self): self.connected = False
    
    def _setfattr(self, key, val): return self.features[key].store(val)

    def poll_feature(self, f, *args, **xargs): f.poll_on_server()

    def send(self, data): pass

    def on_receive_raw_data(self, data):
        called_features = [f for key, f in self.features.items() if f.call == data]
        if called_features:
            # data is a request
            for f in called_features: self.poll_feature(f)
        else:
            # data is a command
            super().on_receive_raw_data(data)


class _FeaturesMixin:
    _polled = list
    preload_features = set() # feature keys to be polled on_connect

    def __init__(self, *args, **xargs):
        super().__init__(*args, **xargs)
        self.preload_features = self.preload_features.copy()
        self._polled = self._polled()

    def on_connect(self):
        super().on_connect()
        for key in set(self.preload_features):
            if key in self.features: self.features[key].async_poll()

    def on_disconnected(self):
        super().on_disconnected()
        self._pending.clear()
        self._polled.clear()
        for f in self.features.values(): f.unset()
    
    def mainloop_hook(self):
        super().mainloop_hook()
        for p in self._pending: p.check_expiration()
    
    def poll_feature(self, f, force=False):
        """ poll feature value if not polled before or force is True """
        if f.call in self._polled and not force: return
        self._polled.append(f.call)
        f.poll_on_client()


class _AbstractClient(ProtocolBase):
    """
    Abstract Client
    Note: Event callbacks (on_connect, on_feature_change) might be called in the mainloop
        and delay further command processing. Use threads for not blocking the
        mainloop.
    """
    connected = False
    _mainloopt = None
    _stoploop = None
    _connectOnEnter = False

    def __init__(self, connect=True, *args, **xargs):
        super().__init__(*args, **xargs)
        self._stoploop = Event()
        self._connectOnEnter = connect
    
    def _setfattr(self, key, val): return self.features[key].send(val)

    def enter(self):
        if self._connectOnEnter: self.connect()
        self._stoploop.clear()
        self._mainloopt = Thread(target=self.mainloop, name=self.__class__.__name__, daemon=True)
        self._mainloopt.start()
        return self

    def exit(self):
        self._stoploop.set()
        self.disconnect()
        self._mainloopt.join()
        if self.connected: self.on_disconnected()

    def connect(self): pass

    def disconnect(self): pass

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
        """ Execute when connected to server e.g. after connection aborted """
        self.connected = True
        if self.verbose > 0:
            print("[%s] connected to %s"%(self.__class__.__name__, self.prompt), file=sys.stderr)
        
    @log_call
    def on_disconnected(self): self.connected = False

    def mainloop(self):
        """ listens on server for events and calls on_feature_change. Return when connection closed """
        while not self._stoploop.is_set(): self.mainloop_hook()
        
    def mainloop_hook(self):
        """ This will be called regularly by mainloop """
        pass
    

class AbstractClient(_FeaturesMixin, _AbstractClient): pass


class AbstractProtocol(ProtocolBase):
    Client = AbstractClient
    Server = AbstractServer

    @classmethod
    def new(cls, func, *args, **xargs):
        return cls.getattr(func)(*args, **xargs)

    @classmethod
    def new_client(cls, *args, **xargs):
        return type(cls.__name__, (cls, cls.Client), {})(*args, **xargs)

    @classmethod
    def new_server(cls, *args, **xargs):
        return type(cls.__name__, (cls, cls.Server), {})(*args, **xargs)

    @classmethod
    def new_dummyserver(cls, *args, **xargs):
        """ Returns a server instance that stores bogus values """
        return type(cls.__name__, (DummyServerMixin, cls, cls.Server), {})(*args, **xargs)


import math
from decimal import Decimal
class DummyServerMixin:
    """ Server class that fills feature values with some values """

    default_values = dict(
        name = "Dummy X7800H",
    )

    def poll_feature(self, f, *args, **xargs):
        if f.isset(): val = f.get()
        elif f.key in self.default_values: val = self.default_values[f.key]
        elif getattr(f, "default_value", None): val = f.default_value
        elif isinstance(f, features.IntFeature): val = math.ceil((f.max+f.min)/2)
        elif isinstance(f, features.DecimalFeature): val = Decimal(f.max+f.min)/2
        elif isinstance(f, features.BoolFeature): val = False
        elif isinstance(f, features.SelectFeature): val = f.options[0] if f.options else "?"
        else: raise TypeError("Feature type %s not known."%f)
        #self.on_receive_raw_data(f.encode(val)) # TODO: handle cases where f.call matches but f.matches() is False and maybe f'.matches() is True
        f.store(val)


