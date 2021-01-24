"""
Dry software run that acts like a real amp
"""

from .. import AmpType, DummyServer, _ProtocolInheritance
from ..core import TelnetClient


class _ConnectDummyTelnetServer(_ProtocolInheritance):

    def __call__(cls, *args, protocol=None, **xargs):
        server = DummyServer(protocol=protocol, listen_host="127.0.0.1", listen_port=1234) #TODO: port=0
        xargs.update(host="127.0.0.1", port=1234) # TODO: get port from self._server
        client = super().__call__(*args, protocol=protocol, **xargs)
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


class Amp(AmpType):
    protocol = "Telnet Emulator"
    Client = DummyTelnetClient

    def __new__(cls, *args, emulate=None, **xargs):
        return cls.Client(*args, protocol=emulate, **xargs)

