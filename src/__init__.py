import importlib

NAME = "HiFiCon"
PKG_NAME = "hificon"
VERSION = "1.6.2a"


def Amp(*args, protocol=None, cls="Amp", **xargs):
    """ returns amp instance from @protocol module. Read @protocol from config if None """
    from .config import config
    protocol = protocol or config.get("Amp","protocol")
    try:
        module = importlib.import_module(protocol, "%s.protocol"%__name__)
    except ImportError:
        raise ValueError("Amp protocol `%s` not found."%protocol)
    Amp_ = getattr(module, cls)
    return Amp_(*args,**xargs)
    
