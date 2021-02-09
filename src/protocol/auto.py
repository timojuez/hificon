from ..core import AbstractProtocol
from ..amp import discover_amp
from .. import Target


class Auto(AbstractProtocol):
    protocol = "Auto"

    def __new__(self, *args, **xargs):
        return Target(discover_amp(), *args,**xargs)

