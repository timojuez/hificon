"""
Dry software run that acts like a real amp
"""

from .. import DummyClient
from ..common import AbstractProtocol


class Amp(AbstractProtocol):
    protocol = "Emulator"
    
    def __new__(cls, *args, emulate=None, **xargs):
        return DummyClient(*args, protocol=emulate, **xargs)

