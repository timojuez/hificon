"""
Dry software run that acts like a real amp
"""

from .. import ProtocolType, DummyServer, _ProtocolInheritance
from ..core import TelnetClient


class _ConnectDummyTelnetServer(_ProtocolInheritance):

    def __call__(cls, target=None, port=0, *args, **xargs):
        server = DummyServer(target, listen_host="127.0.0.1", listen_port=int(port))
        xargs.update(host=server.host, port=server.port)
        client = super().__call__(target, *args, **xargs)
        client._server = server
        return client


class DummyTelnetClient(metaclass=_ConnectDummyTelnetServer):
    _parent = staticmethod(lambda Protocol: TelnetClient)
    _server = None
    
    def enter(self):
        self._server.enter()
        super().enter()
    
    def exit(self):
        super().exit()
        self._server.exit()


class Amp(ProtocolType):
    protocol = "Telnet Emulator"
    Client = DummyTelnetClient

    def __new__(cls, *args, **xargs):
        return cls.Client(*args, **xargs)

