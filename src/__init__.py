import importlib
import math
from decimal import Decimal
from .core import AmpType, config, AbstractProtocol, AbstractServer, AbstractClient, features
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


class _ProtocolInheritance(type):
    """ Adds first parameter @protocol (str) to __init__ and will inherit a class cls from
    (Protocol, cls._parent(Protocol)) where @protocol points at Protocol module.
    Read @protocol from config if None """

    def __call__(cls, *args, protocol=None, **xargs):
        Protocol = Amp_cls(protocol=protocol)
        Complete = type(cls.__name__, (cls, Protocol, cls._parent(Protocol)), {})
        return super(_ProtocolInheritance, Complete).__call__(*args, **xargs)


class Client(metaclass=_ProtocolInheritance):
    _parent = staticmethod(lambda Protocol: Protocol.Client)


class Server(metaclass=_ProtocolInheritance):
    _parent = staticmethod(lambda Protocol: Protocol.Server)


class DummyServer(Server):
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
        f.store(val)


class LocalDummyServer(DummyServer):
    """ DummyServer that acts only inside the process like a variable """
    _parent = staticmethod(lambda Protocol: AbstractServer)


class _ConnectLocalDummyServer(_ProtocolInheritance):

    def __call__(cls, *args, protocol=None, **xargs):
        client = super().__call__(*args, protocol=None, **xargs)
        server = LocalDummyServer(protocol=protocol)
        client.bind(send = lambda data: server.on_receive_raw_data(data))
        server.bind(send = lambda data: client.on_receive_raw_data(data))
        return client


class DummyClient(metaclass=_ConnectLocalDummyServer):
    """ This client class connects to an internal server instance """
    host = "emulator"
    _parent = staticmethod(lambda Protocol: AbstractClient)

    def __init__(self, *args, **xargs):
        super().__init__(*args, **xargs)
        self.port = None

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


Amp = Client

