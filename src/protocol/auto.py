from ..amp import AbstractAmp, discover_amp
from .. import Amp as Amp_


class Amp(AbstractAmp):
    protocol = "Auto"

    def __new__(self, *args, **xargs):
        xargs.update(discover_amp())
        return Amp_(*args,**xargs)

