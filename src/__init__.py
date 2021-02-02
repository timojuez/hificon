import importlib
from .core import ProtocolType, config, AbstractProtocol, AbstractServer, AbstractClient, features
from .info import *


def get_protocol(cls):
    """ @cls str: Class name in .protocol or "module.class" """
    if "." in cls: module_path, cls = cls.rsplit(".", 1)
    else: module_path = "."
    module = importlib.import_module(module_path, "%s.protocol"%__name__)
    Protocol = getattr(module, cls)
    assert(issubclass(Protocol, ProtocolType))
    return Protocol


def Target(uri=None, role="client", *args, **xargs):
    """
    Returns a protocol instance. The protocol class path must be contained in the URI.
    @uri: URI to connect to. Schema: protocol_cls:arg_1:...:arg_n. Will be read from config by default.
        Examples:
            denon://192.168.1.15:23
            emulator:denon
    @role: Method "new_@role" will be called on the protocol for instantiation. Can be "server" or "client".
    """
    uri = (uri or config.get("Target","uri")).split(":")
    Protocol = getattr(get_protocol(uri.pop(0)), f"new_{role}")
    return Protocol(*uri, *args, **xargs)


Amp = Target

