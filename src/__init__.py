import importlib
import math
from decimal import Decimal
from .common import AmpType, config, AbstractProtocol, AbstractServer, AbstractClient, features
from .info import *


def Amp_cls(protocol=None, cls="Amp"):
    """ returns amp instance from @protocol module. Read @protocol from config if None """
    protocol = protocol or config.get("Connection","protocol")
    try:
        module = importlib.import_module(protocol, "%s.protocol"%__name__)
    except ImportError:
        raise ValueError("Amp protocol `%s` not found."%protocol)
    Protocol = getattr(module, cls)
    assert(issubclass(Protocol, AmpType))
    return Protocol


class Client:

    def __new__(cls, *args, protocol=None, **xargs):
        """ returns amp instance from @protocol module. Read @protocol from config if None """
        Protocol = Amp_cls(protocol=protocol)
        Client = type("Client", (cls, Protocol, Protocol.Client), {})
        return Protocol.__new__(Client)
    
    def __init__(self, *args, protocol=None, **xargs): super().__init__(*args, **xargs)


class Server:

    def __new__(cls, *args, protocol=None, **xargs):
        """ returns amp instance from @protocol module. Read @protocol from config if None """
        Protocol = Amp_cls(protocol=protocol)
        Server = type("Server", (cls, Protocol, Protocol.Server), {})
        return Protocol.__new__(Server)
    
    def __init__(self, *args, protocol=None, **xargs): super().__init__(*args, **xargs)


class _DummyServer:
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
        f.store(val)


class DummyServer(_DummyServer, Server): pass


class DummyClient:
    """ This client class connects to an internal server instance """
    host = "emulator"
    _server = None

    def __new__(cls, *args, protocol=None, **xargs):
        """ returns amp instance from @protocol module. Read @protocol from config if None """
        Protocol = Amp_cls(protocol)
        Client = type("Client",(cls, Protocol, AbstractClient), {})
        return Protocol.__new__(Client, *args, **xargs)

    def __init__(self, *args, protocol=None, **xargs):
        super().__init__(*args, **xargs)
        Server = type("Server",(_DummyServer, Amp_cls(protocol), AbstractServer),{})
        self._server = Server()
        self.port = None
        assert(isinstance(self._server, AbstractServer))
        self._server.bind(send = lambda data: self.on_receive_raw_data(data))

    def connect(self):
        super().connect()
        self.on_connect()

    def disconnect(self):
        super().disconnect()
        self.on_disconnected()

    def mainloop(self):
        if not self.connected: self.connect()
    
    def send(self, data):
        super().send(data)
        if not self.connected: raise BrokenPipeError("Not connected")
        return self._server.on_receive_raw_data(data)


Amp = Client

