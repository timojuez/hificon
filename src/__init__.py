import importlib
from urllib.parse import parse_qsl
from .core import ProtocolType, config, AbstractProtocol, AbstractServer, AbstractClient, features
from .info import *
from .protocol import protocols


def get_protocols():
    for p in protocols.keys(): yield get_protocol(p)


def get_protocol(cls_path):
    """ @cls_path str: Key in .protocol.protocols or "module.class" """
    try: cls_path_ = protocols[cls_path]
    except KeyError: cls_path_ = cls_path
    module_path, cls = cls_path_.rsplit(".", 1)
    module = importlib.import_module(module_path, "%s.protocol"%__name__)
    Protocol = getattr(module, cls)
    Protocol.protocol = cls_path
    assert(issubclass(Protocol, ProtocolType))
    return Protocol


def Target(uri=None, role="client", *args, **xargs):
    """
    Returns a protocol instance. The protocol class path must be contained in the URI.
    @uri: URI to connect to. Schema: protocol_cls:arg_1:...:arg_n. Will be read from config by default.
        Examples:
            denon://192.168.1.15:23
            emulate:denon
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

