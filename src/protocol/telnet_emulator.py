"""
Dry software run that acts like a real amp
"""

from ..core.transport import ProtocolType, TelnetClient
from .. import Target, Amp_cls


class DummyTelnetClient:
    """ This client class automatically connects to a dummy server instance """
    _server = None

    def enter(self):
        self._server.enter()
        super().enter()
    
    def exit(self):
        super().exit()
        self._server.exit()


class Amp(ProtocolType):
    protocol = "Telnet Emulator"

    @classmethod
    def new_client(cls, protocol, port=0, *args, **xargs):
        Protocol = Amp_cls(protocol)
        server = Protocol.new_dummyserver(listen_host="127.0.0.1", listen_port=int(port))
        xargs.update(host=server.host, port=server.port)
        client = type(Protocol.__name__, (DummyTelnetClient, Protocol, TelnetClient), {})(*args, **xargs)
        client._server = server
        return client
    
    @classmethod
    def new_server(*args, **xargs): raise NotImplementedError()

