import importlib
from urllib.parse import parse_qsl
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
    if uri and "?" in uri: uri, query = uri.split("?",1)
    else: query = None
    if not uri: uri = config.get("Target", "uri").split("?",1)[0]
    uri = uri.split(":")
    Protocol = getattr(get_protocol(uri.pop(0)), f"new_{role}")
    target = Protocol(*uri, *args, **xargs)
    if query:
        with target:
            for key, val in parse_qsl(query, True):
                if val: # ?fkey=val
                    f = target.features[key]
                    convert = {bool: lambda s:s[0].lower() in "yt1"}.get(f.type, f.type)
                    f.send(convert(val), force=True)
                else: target.send(key) # ?COMMAND
    return target

