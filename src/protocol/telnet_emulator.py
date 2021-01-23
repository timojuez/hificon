"""
Dry software run that acts like a real amp
"""

from .. import DummyServer, Amp_cls
from ..core import TelnetClient, TelnetProtocol


class DummyTelnetClient(TelnetClient):
    _server = None
    
    def __init__(self, *args, emulate=None, **xargs):
        self._server = DummyServer(protocol=emulate, listen_host="127.0.0.1", listen_port=1234) #TODO: port=0
        xargs.update(host="127.0.0.1", port=1234) # TODO: get port from self._server
        super().__init__(*args, **xargs)

    def enter(self):
        self._server.enter()
        super().enter()
    
    def exit(self):
        super().exit()
        self._server.exit()


class Amp(TelnetProtocol):
    protocol = "Telnet Emulator"
    Server = None
    Client = DummyTelnetClient

    def __new__(cls, *args, emulate=None, **xargs): # TODO: move to metaclass for DummyTelnetClient
        return type("Client", (Amp_cls(emulate), DummyTelnetClient), {})(*args, emulate=emulate, **xargs)

