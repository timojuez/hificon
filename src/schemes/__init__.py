import importlib
from ..core.transmission import SchemeType

schemes = {
    "denon": ".denon.Denon",
    "emulate": ".emulate.Emulate",
    "plain_emulate": ".emulate.PlainEmulate",
    "raw_telnet": ".raw_telnet.RawTelnet",
    "auto": ".auto.Auto",
    "repeat": ".repeat.Repeat"
}


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
    module = importlib.import_module(module_path, __name__)
    Scheme = getattr(module, cls)
    Scheme.scheme = cls_path
    Scheme.Scheme = Scheme
    assert(issubclass(Scheme, SchemeType))
    return Scheme

