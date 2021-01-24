"""
Dry software run that acts like a real amp
"""

from .. import ProtocolType, DummyClient


class Amp(ProtocolType):
    protocol = "Emulator"
    Client = DummyClient
    
    def __new__(cls, *args, **xargs):
        return cls.Client(*args, **xargs)

