import importlib
from urllib.parse import parse_qsl
from .core import config, AbstractScheme, AbstractServer, AbstractClient, features
from .info import *
from .schemes import schemes


def get_schemes():
    for p in schemes.keys(): yield get_scheme(p)


def get_scheme(cls_path):
    """ @cls_path str: Key in .schemes.schemes or "module.class" """
    try: cls_path_ = schemes[cls_path]
    except KeyError: cls_path_ = cls_path
    if "." not in cls_path_:
        schemes_str = ", ".join(schemes.keys())
        raise ValueError(f"cls_path must be {schemes_str} or MODULE.CLASS but was '{cls_path}'.")
    module_path, cls = cls_path_.rsplit(".", 1)
    module = importlib.import_module(module_path, "%s.schemes"%__name__)
    Scheme = getattr(module, cls)
    Scheme.scheme = cls_path
    assert(issubclass(Scheme, AbstractScheme))
    return Scheme


def Target(uri=None, *args, role="client", **xargs):
    """
    Returns a scheme instance. The scheme class path must be contained in the URI.
    @uri: URI to connect to. Syntax: scheme_cls:arg_1:...:arg_n. Will be read from config by default.
        Examples:
            denon://192.168.1.15:23
            emulate:denon
            ?volume=20
    @role: Method "new_@role" will be called on the scheme for instantiation. Can be "client", "server" or "dummyserver".
    """
    if uri and "?" in uri: uri, query = uri.split("?",1)
    else: query = None
    if not uri: uri = config.get("Target", "uri").split("?",1)[0]
    uri = uri.split(":")
    Scheme = getattr(get_scheme(uri.pop(0)), f"new_{role}")
    target = Scheme(*uri, *args, **xargs)
    if query:
        with target:
            for key, val in parse_qsl(query, True):
                if val: # ?fkey=val
                    f = target.features[key]
                    convert = {bool: lambda s:s[0].lower() in "yt1"}.get(f.type, f.type)
                    target.set_feature_value(f, convert(val))
                else: target.send(key) # ?COMMAND #FIXME: use target.on_receive_raw_data for server
    return target

