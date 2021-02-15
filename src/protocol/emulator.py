"""
Dry software run that emulates a protocol and acts like a real target
"""

from .. import get_protocol
from ..core.transport import ProtocolType, TelnetProtocol
from ..core.transport.abstract import DummyServerMixin, AbstractClient, AbstractServer


class DummyClientMixin:
    """ This client class automatically connects to an internal server instance """
    _server = None

    def enter(self):
        self._server.enter()
        super().enter()
    
    def exit(self):
        super().exit()
        self._server.exit()


class PlainDummyClientMixin(DummyClientMixin):
    """ This client skips connection related methods """

    def __init__(self, server, *args, **xargs):
        super().__init__(*args, **xargs)
        self._server = server
        server.bind(send = lambda data: self.on_receive_raw_data(data))
        self.bind(send = lambda data: server.on_receive_raw_data(data))

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


class Emulator(ProtocolType):
    protocol = "Emulator"

    @classmethod
    def new_client(cls, protocol, *args, **xargs):
        Protocol = get_protocol(protocol)
        server = cls.new_server(protocol)
        Client = type(Protocol.__name__, (DummyClientMixin, Protocol, Protocol.Client), {"_server":server})
        return Client(server, *args, **xargs)

    @classmethod
    def new_server(cls, protocol, *args, **xargs):
        Protocol = get_protocol(protocol)
        return Protocol.new_dummyserver(*args, **xargs)


class PlainEmulator(ProtocolType):
    """ Emulator without network connection. Only internal variables are being used. """
    protocol = "Plain Emulator"

    @classmethod
    def new_client(cls, protocol, *args, **xargs):
        Client = type("Client", (PlainDummyClientMixin, get_protocol(protocol), AbstractClient), {})
        return Client(cls.new_server(protocol), *args, **xargs)

    @classmethod
    def new_server(cls, protocol, *args, **xargs):
        Protocol = get_protocol(protocol)
        return type("Server", (DummyServerMixin, Protocol, AbstractServer), {})(*args, **xargs)

