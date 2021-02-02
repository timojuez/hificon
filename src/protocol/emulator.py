"""
Dry software run that acts like a real amp
"""

from .. import get_protocol
from ..core.transport import ProtocolType, TelnetProtocol
from ..core.transport.abstract import DummyServerMixin, AbstractClient, AbstractServer


class DummyClientMixin:
    """ This client class automatically connects to an internal server instance """
    host = "emulator"
    _server = None

    def __init__(self, *args, **xargs):
        super().__init__(*args, **xargs)
        self.port = None

    def connect(self):
        super().connect()
        self.on_connect()

    def disconnect(self):
        super().disconnect()
        self.on_disconnected()

    def mainloop(self):
        if not self.connected: self.connect()
    
    def send(self, data):
        super().send(data)
        if not self.connected: raise BrokenPipeError("Not connected")

    def enter(self):
        self._server.enter()
        super().enter()
    
    def exit(self):
        super().exit()
        self._server.exit()


class DummyTelnetClient:
    """ This client class automatically connects to a dummy server instance """
    _server = None

    def enter(self):
        self._server.enter()
        super().enter()
    
    def exit(self):
        super().exit()
        self._server.exit()


class TelnetEmulator(ProtocolType):
    protocol = "Telnet Emulator"

    @classmethod
    def new_client(cls, protocol, port=0, *args, **xargs):
        print(protocol)
        Protocol = get_protocol(protocol)
        server = Protocol.new_dummyserver(listen_host="127.0.0.1", listen_port=int(port))
        xargs.update(host=server.host, port=server.port)
        client = type(Protocol.__name__, (DummyTelnetClient, Protocol, Protocol.Client), {})(*args, **xargs)
        client._server = server
        return client
    
    @classmethod
    def new_server(*args, **xargs): raise NotImplementedError()


class PlainEmulator(ProtocolType):
    protocol = "Plain Emulator"
    
    @classmethod
    def new_client(cls, protocol, *args, **xargs):
        Protocol = get_protocol(protocol)
        server = type("Server", (DummyServerMixin, Protocol, AbstractServer), {})()
        client = type("Client", (DummyClientMixin, Protocol, AbstractClient), {})(*args, **xargs)
        client._server = server
        server.bind(send = lambda data: client.on_receive_raw_data(data))
        client.bind(send = lambda data: server.on_receive_raw_data(data))
        return client
    
    @classmethod
    def new_server(*args, **xargs): raise NotImplementedError()


class Emulator(ProtocolType):
    protocol = "Emulator"

    @classmethod
    def new_client(cls, protocol, *args, **xargs):
        Protocol = get_protocol(protocol)
        Emulator = TelnetEmulator if issubclass(Protocol, TelnetProtocol) else PlainEmulator
        return Emulator.new_client(protocol, *args, **xargs)

    @classmethod
    def new_server(*args, **xargs): raise NotImplementedError()

