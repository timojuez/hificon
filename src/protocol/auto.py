from ..amp import AbstractAmp, discover_amp
from .. import Amp as Amp_


class Auto(AbstractAmp):
    protocol = "Auto"

    def __new__(self, *args, **xargs):
        return Amp_(discover_amp(), *args,**xargs)

