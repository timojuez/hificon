from ..core import AbstractScheme
from ..core.transmission.discovery import discover_target
from .. import Target


class Auto(AbstractScheme):
    description = "Detect a supported server in network by using SSDP"
    client_args_help = tuple()

    def __new__(self, *args, **xargs):
        return Target(discover_target().uri, *args, **xargs)

