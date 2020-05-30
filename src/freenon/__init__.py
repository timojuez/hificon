import importlib
from .amp import *
from .config import config


def Amp(*args, protocol=None, cls="Amp", **xargs):
    protocol = protocol or config.get("AVR","protocol")
    try:
        module = importlib.import_module(protocol)
    except ImportError:
        raise RuntimeError("AVR protocol `%s` not found."%protocol)
    Amp_ = getattr(module, cls)
    return Amp_(*args,**xargs)
    
