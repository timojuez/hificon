import importlib

NAME = "HiFiCon"
PKG_NAME = "hificon"
VERSION = "1.10.0a"
AUTHOR = "Timo L. Richter"
URL = 'https://github.com/timojuez/hificon'
COPYRIGHT = ("Copyright \xa9 2021 %s\n"
    "Icons based on Ubuntu Mono Dark (GNU GPLv3)")%AUTHOR


def Amp_cls(protocol=None, cls="Amp"):
    """ returns amp instance from @protocol module. Read @protocol from config if None """
    from .amp import AmpType
    from .common.config import config
    protocol = protocol or config.get("Connection","protocol")
    try:
        module = importlib.import_module(protocol, "%s.protocol"%__name__)
    except ImportError:
        raise ValueError("Amp protocol `%s` not found."%protocol)
    Protocol = getattr(module, cls)
    assert(issubclass(Protocol, AmpType))
    return Protocol


def Amp(*args, protocol=None, cls="Amp", **xargs):
    return Amp_cls(protocol, cls).Client(*args,**xargs)
    
