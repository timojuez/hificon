import importlib
from .amp import *
from .config import config


def Amp(*args, protocol=None, cls="Amp", **xargs):
    protocol = protocol or config.get("Amp","protocol")
    try:
        module = importlib.import_module(protocol, "%s.protocol"%__name__)
    except ImportError:
        raise RuntimeError("Amp protocol `%s` not found."%protocol)
    Amp_ = getattr(module, cls)
    return Amp_(*args,**xargs)
    
