"""
Dry software run that acts like a real amp
"""

from .. import Amp_cls
from ..core.transport import ProtocolType
from ..core.transport.abstract import DummyServerMixin, AbstractClient, AbstractServer


class DummyClientMixin:
    """ This client class connects to an internal server instance """
    host = "emulator"

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


class Amp(ProtocolType):
    protocol = "Emulator"
    
    @classmethod
    def new_client(cls, protocol, *args, **xargs):
        Protocol = Amp_cls(protocol)
        server = type("Server", (DummyServerMixin, Protocol, AbstractServer), {})()
        client = type("Client", (DummyClientMixin, Protocol, AbstractClient), {})(*args, **xargs)
        server.bind(send = lambda data: client.on_receive_raw_data(data))
        client.bind(send = lambda data: server.on_receive_raw_data(data))
        return client
    
    @classmethod
    def new_server(*args, **xargs): raise NotImplementedError()

