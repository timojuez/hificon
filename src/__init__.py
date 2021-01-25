import importlib
from .core import ProtocolType, config, AbstractProtocol, AbstractServer, AbstractClient, features
from .info import *


def Amp_cls(protocol=None, cls="Amp"):
    """ returns Amp class from @protocol module """
    try:
        module = importlib.import_module(protocol, "%s.protocol"%__name__)
    except ImportError:
        raise ValueError("Amp protocol `%s` not found."%protocol)
    Protocol = getattr(module, cls)
    assert(issubclass(Protocol, ProtocolType))
    return Protocol


def Target(uri=config.get("Target","uri"), role="client", *args, **xargs):
    """
    Returns a protocol instance. The protocol class path must be contained in the URI.
    @uri: URI to connect to. Schema: protocol_module:arg_1:...:arg_n. Example: .denon://192.168.1.15:23
        Will be read from config by default.
    @role: Method "new_@role" will be called on the protocol for instantiation. Can be "server" or "client".
    """
    uri = uri.split(":")
    Protocol = getattr(Amp_cls(protocol=uri.pop(0)), f"new_{role}")
    return Protocol(*uri, *args, **xargs)


Amp = Target

