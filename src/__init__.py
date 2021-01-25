import importlib
from .core import ProtocolType, config, AbstractProtocol, AbstractServer, AbstractClient, features
from .info import *


def Amp_cls(protocol=None, cls="Amp"):
    """ returns amp instance from @protocol module. Read @protocol from config if None """
    try:
        module = importlib.import_module(protocol, "%s.protocol"%__name__)
    except ImportError:
        raise ValueError("Amp protocol `%s` not found."%protocol)
    Protocol = getattr(module, cls)
    assert(issubclass(Protocol, ProtocolType))
    return Protocol


def Target(uri=None, method="client", *args, **xargs): #Communication, Target, Transport, Protocol?
    """ Adds first parameter @protocol (str) to __init__ and will inherit a class cls from
    (Protocol, cls._parent(Protocol)) where @protocol points at Protocol module.
    @target is a URI in the scheme protocol_module:arg_1:...:arg_n, e.g. .denon://127.0.0.1:23
    Read @target from config if None """
    uri = uri or f'{config.get("Connection","protocol")}://{config.get("Connection","host")}:{config.get("Connection","port")}'
    uri = uri.split(":")
    Protocol = getattr(Amp_cls(protocol=uri.pop(0)), f"new_{method}")
    return Protocol(*uri, *args, **xargs)


Amp = Target

