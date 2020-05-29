from .amp import *
from .config import config


def Amp(*args, protocol=None, cls="Amp", **xargs):
    protocol = protocol or config.get("AVR","protocol")
    if protocol == "Denon":
        from . import denon
        Amp_ = getattr(denon, cls)
        return Amp_(*args,**xargs)
    else:
        raise RuntimeError("AVR protocol `%s` not supported."%protocol)


