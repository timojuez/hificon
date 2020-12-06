import importlib
from ..bin.setup import discover_amp

host, name, protocol = discover_amp()
module = importlib.import_module(protocol, __name__.rpartition(".")[0])

class Amp(module.Amp):
    name = name
    host = host

