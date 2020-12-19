from ..amp import AbstractAmp
from .. import Amp as Amp_
from ..common.amp_discovery import discover_amp


class Amp(AbstractAmp):
    protocol = "Auto"

    def __new__(self, *args, **xargs):
        xargs.update(discover_amp())
        return Amp_(*args,**xargs)

