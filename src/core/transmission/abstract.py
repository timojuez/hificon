"""
The classes AbstractClient and TelnetClient help you to stay synchronised with
values from a Telnet or non-Telnet server. A client supports features. See features.py.
"""

import sys, re
from urllib.parse import parse_qsl
from threading import Thread, Event
from ..util.function_bind import Bindable
from ..util import log_call
from .types import SchemeType, ServerType, ClientType
from .discovery import DiscoverySchemeMixin
from . import features


class AbstractTarget(Bindable):
    """ A server or client instance """
    verbose = 0
    connected = False
    uri = ""
    scheme = "[undefined]"
    Scheme = None
    features = features.Features()
    feature_categories = property(lambda self: self.Scheme.feature_categories)
    _pending = list

    def __init__(self, *args, verbose=0, **xargs):
        self.verbose = verbose
        self.update_uri()
        self.features = self.features.__class__()
        self._pending = self._pending()
        # apply @features to self
        for F in self.Scheme.features.values(): F(self)
        super().__init__(*args, **xargs)

    def __eq__(self, target):
        return (isinstance(target, AbstractTarget)
            and self.uri == target.uri
            and isinstance(self, self.Scheme.Client) == isinstance(target, self.Scheme.Client))

    def __enter__(self): self.enter(); return self

    def __exit__(self, type, value, tb): self.exit()

    def enter(self): pass
    
    def exit(self): pass

    def update_uri(self, *args): self.uri = ":".join(map(str, [self.scheme, *args]))

    def poll_feature(self, f, *args, **xargs):
        """ Called when a feature value is being requested """
        raise NotImplementedError()

    def on_receive_feature_value(self, f, value):
        """ Called when a value is being received from the other side """
        raise NotImplementedError()

    def set_feature_value(self, f, value):
        """ Set a value through the framework. Usually, on a client this will call f.remote_set() """
        raise NotImplementedError()

    def schedule(self, func, args=tuple(), kwargs={}, requires=tuple()):
        """ Use this to call methods that use Target.features.
        Call func(*args, **xargs) if all features in @requires are set.
        Poll features and schedule func otherwise. """
        if not self.connected: return
        try: features_ = [self.features[name] for name in requires]
        except KeyError as e:
            if self.verbose > 3:
                print("[%s] Warning: Target does not provide feature required by `%s`: %s"
                %(self.__class__.__name__, func.__name__, e), file=sys.stderr)
        else: return features.FunctionCall(self, func, args, kwargs, features_)

    @log_call
    def on_feature_change(self, f_id, value):
        """ attribute on server has changed """
        if f_id and self.verbose > 2:
            print("[%s] $%s = %s"%(self.__class__.__name__,f_id,repr(value)))
        
    def send(self, data): raise NotImplementedError()

    def on_receive_raw_data(self, data):
        if self.verbose > 4: print(data, file=sys.stderr)
        consumed = [f.consume(data) for f_id,f in self.features.items() if f.matches(data)]
        if not consumed: self.features.fallback.consume(data)

    def handle_query(self, query):
        for key, val in parse_qsl(query, True):
            if val: # ?fkey=val
                f = self.features[key]
                convert = {bool: lambda s:s[0].lower() in "yt1"}.get(f.type, f.type)
                self.set_feature_value(f, convert(val))
            else: self.send(key) # ?COMMAND #FIXME: use self.on_receive_raw_data for server


class AttachedClientMixin:
    """ This client class automatically connects to an internal server instance """
    _server = None
    _control_server = False

    def enter(self):
        if control_server := not self._server.connected: self._server.enter()
        self._control_server = control_server
        super().enter()

    def exit(self):
        if self._control_server: self._server.exit()
        super().exit()


class AbstractServer(ServerType, AbstractTarget):
    init_args_help = None # tuple

    def __init__(self, *args, **xargs):
        super().__init__(*args, **xargs)
        for f in self.features.values(): f.init_on_server()
        for f in self.features.values():
            not f.id=="fallback" and f.bind(on_change=lambda *_,f=f: self.connected and f.resend())
    
    def enter(self): self.connected = True
    def exit(self): self.connected = False
    
    def new_attached_client(self, *args, **xargs):
        """ return new Client instance that connects to this server. Should be overwritten in inheriting classes """
        Client = self.Scheme._new_target(self.Scheme.Client)
        AttachedClient = type(Client.__name__, (AttachedClientMixin, Client), {"_server":self})
        return AttachedClient(*args, **xargs)

    def set_feature_value(self, f, value): return f.set(value)

    def poll_feature(self, f, *args, **xargs): f.poll_on_server()

    def on_receive_feature_value(self, f, value): f.set_on_server(value)

    def send(self, data): pass

    def on_receive_raw_data(self, data):
        called_features = [f for f_id, f in self.features.items() if f.call == data]
        if called_features:
            # data is a request
            for f in called_features:
                if f.isset(): f.resend()
                else: self.poll_feature(f)
        else:
            # data is a command
            super().on_receive_raw_data(data)


class _FeaturesMixin:
    _polled = list
    preload_features = set() # feature ids to be polled on_connect

    def __init__(self, *args, **xargs):
        super().__init__(*args, **xargs)
        self.preload_features = self.preload_features.copy()
        self._polled = self._polled()

    def on_connect(self):
        super().on_connect()
        for f_id in set(self.preload_features):
            if f_id in self.features: self.features[f_id].async_poll()

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

    def on_receive_feature_value(self, f, value): f.set(value)

    def set_feature_value(self, f, value): f.remote_set(value)


class _AbstractClient(ClientType, AbstractTarget):
    """
    Abstract Client
    Note: Event callbacks (on_connect, on_feature_change) might be called in the mainloop
        and delay further command processing. Use threads for not blocking the
        mainloop.
    """
    init_args_help = None # tuple
    connected = False
    _mainloopt = None
    _stoploop = None
    _connectOnEnter = False

    def __init__(self, *args, connect=True, **xargs):
        super().__init__(*args, **xargs)
        self._stoploop = Event()
        self._connectOnEnter = connect
    
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
        if matches is None: return self.send(cmd)
        raise NotImplementedError()

    __call__ = lambda self,*args,**xargs: self.query(*args,**xargs)
        
    def send(self, cmd):
        if self.verbose > 4: print(f"{self.uri} $ ${repr(cmd)}", file=sys.stderr)

    @log_call
    def on_connect(self):
        """ Execute when connected to server e.g. after connection aborted """
        self.connected = True
        if self.verbose > 0:
            print("[%s] connected to %s"%(self.__class__.__name__, self.uri), file=sys.stderr)
        
    @log_call
    def on_disconnected(self): self.connected = False

    def mainloop(self):
        """ listens on server for events and calls on_feature_change. Return when connection closed """
        while not self._stoploop.is_set(): self.mainloop_hook()
        
    def mainloop_hook(self):
        """ This will be called regularly by mainloop """
        pass

    def handle_query(self, *args, **xargs):
        self.connect()
        super().handle_query(*args, **xargs)


class AbstractClient(_FeaturesMixin, _AbstractClient): pass


class _AbstractSchemeMeta(type):

    def __init__(cls, name, bases, dct):
        cls.features = cls.features.copy()
        cls.feature_categories = cls.feature_categories.copy()

    # the following methods are only available on class

    def get_client_uri(cls):
        args = cls.client_args_help
        if args is None: args = getattr(cls.Client,"init_args_help",None)
        if args is not None: return ":".join((cls.scheme, *args))

    def get_server_uri(cls):
        args = cls.server_args_help
        if args is None: args = getattr(cls.Server,"init_args_help",None)
        if args is not None: return ":".join((cls.scheme, *args))

    def add_feature(cls, Feature=None, overwrite=False):
        """
        This is a decorator to be used on Feature class definitions that belong to the current class.
        @overwrite: If true, proceeds if a feature with same id already exists.
        Example:
            from client.feature import Feature
            @AbstractClient.add_feature
            class MyFeature(Feature): pass
        """
        def add(Feature, overwrite=overwrite):
            if not issubclass(Feature, features.Feature):
                raise TypeError(f"Feature must be of type {features.Feature}")
            if Feature.id.startswith("_"): raise KeyError("Feature.id may not start with '_'")
            if hasattr(cls.features.__class__, Feature.id):
                raise KeyError("Feature.id `%s` is already occupied."%Feature.id)
            if not overwrite and Feature.id in cls.features:
                raise KeyError(
                    "Feature.id `%s` is already occupied. Use add_feature(overwrite=True)"%Feature.id)
            cls.features.pop(Feature.id, None)
            cls.features[Feature.id] = Feature
            cls.feature_categories[Feature.category] = None
            return Feature
        return add(Feature) if Feature else add


class AbstractScheme(DiscoverySchemeMixin, SchemeType, metaclass=_AbstractSchemeMeta):
    title = None
    description = None
    Client = AbstractClient
    Server = AbstractServer
    client_args_help = None # tuple, if None, will be read from Client.init_args_help
    server_args_help = None # tuple
    features = features.Features()
    feature_categories = dict()

    @classmethod
    def _new_target(cls, base):
        if issubclass(cls, AbstractTarget): raise TypeError(
            f"Cannot run method on concrete class. Call this on self.Scheme (class {cls.__name__}).")
        return type(cls.__name__, (cls, base), {"Scheme": cls})

    @classmethod
    def new_client(cls, *args, **xargs):
        return cls._new_target(cls.Client)(*args, **xargs)

    @classmethod
    def new_server(cls, *args, **xargs):
        return cls._new_target(cls.Server)(*args, **xargs)

    @classmethod
    def new_dummyserver(cls, *args, **xargs):
        """ Returns a server instance that stores bogus values """
        DummyServer = type("DummyServer", (DummyServerMixin, cls.Server), {})
        return cls._new_target(DummyServer)(*args, **xargs)

    @classmethod
    def get_title(cls): return cls.title or re.sub(r'(?<!^)(?=[A-Z])', ' ', cls.__name__)


class DummyServerMixin:
    """ Server class that fills feature values with some values """

    def poll_feature(self, f, *args, **xargs): f.poll_on_dummy()

    def on_receive_feature_value(self, f, value):
        if isinstance(f, features.NumericFeature) and not (f.min <= value <= f.max): return
        f.set(value)


@AbstractScheme.add_feature
class Fallback(features.OfflineFeatureMixin, features.SelectFeature):
    """ Matches always, if no other feature matched """
    name = "Last Unexpected Message"

    def consume(self, data):
        if self.target.verbose > 1:
            print("[%s] WARNING: could not parse `%s`"%(self.__class__.__name__, data))
        with self._lock:
            self._prev_val = self._val
            self._val = data
            self.on_change(data)
            if self._prev_val == None: self.on_set()
            self.on_processed(data)


@AbstractScheme.add_feature
class Name(features.OfflineFeatureMixin, features.SelectFeature):
    
    def get(self): return self.target.Scheme.get_title()
    def isset(self): return True
    def unset(self): pass

