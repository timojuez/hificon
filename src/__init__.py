import importlib

NAME = "HiFiCon"
PKG_NAME = "hificon"
VERSION = "1.8.30a"


def Amp_cls(protocol=None, cls="Amp"):
    """ returns amp instance from @protocol module. Read @protocol from config if None """
    from .config import config
    protocol = protocol or config.get("Amp","protocol")
    try:
        module = importlib.import_module(protocol, "%s.protocol"%__name__)
    except ImportError:
        raise ValueError("Amp protocol `%s` not found."%protocol)
    return getattr(module, cls)


def Amp(*args, protocol=None, cls="Amp", **xargs):
    return Amp_cls(protocol, cls)(*args,**xargs)
    
