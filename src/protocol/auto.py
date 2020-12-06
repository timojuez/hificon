import importlib
from ..amp import AbstractAmp
from ..bin.setup import discover_amp


class Amp(AbstractAmp):
    protocol = "Auto"

    def __new__(self, *args, **xargs):
        host_, name_, protocol = discover_amp()
        module = importlib.import_module(protocol, __name__.rpartition(".")[0])

        class Amp_(module.Amp):
            name = name_
            host = host_
        
        return Amp_(*args, **xargs)

