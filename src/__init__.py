import importlib

NAME = "HiFiCon"
PKG_NAME = "hificon"


def Amp(*args, protocol=None, cls="Amp", **xargs):
    from .config import config
    protocol = protocol or config.get("Amp","protocol")
    try:
        module = importlib.import_module(protocol, "%s.protocol"%__name__)
    except ImportError:
        raise ValueError("Amp protocol `%s` not found."%protocol)
    Amp_ = getattr(module, cls)
    return Amp_(*args,**xargs)
    
