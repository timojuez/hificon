"""
Dry software run that emulates a target of another scheme
"""

from .. import get_scheme
from ..core.transport import SchemeType, TelnetScheme
from ..core.transport.abstract import DummyServerMixin, AbstractClient, AbstractServer


class DummyClientMixin:
    """ This client class automatically connects to an internal server instance """
    _server = None

    def enter(self):
        self._server.enter()
        super().enter()
    
    def exit(self):
        self._server.exit()
        super().exit()


class PlainDummyClientMixin(DummyClientMixin):
    """ This client skips connection related methods """

    def __init__(self, server, *args, **xargs):
        super().__init__(*args, **xargs)
        self._server = server
        server.bind(send = lambda data: self.on_receive_raw_data(data))
        self.bind(send = lambda data: server.on_receive_raw_data(data))
        self.uri = f"emulate:{self.scheme}"

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


class Emulate(SchemeType):
    title = "Emulator"
    description = "Emulates a target"
    client_args_help = ("SCHEME",)
    server_args_help = ("SCHEME",)

    @classmethod
    def new_client(cls, scheme, *args, **xargs):
        Scheme = get_scheme(scheme)
        server = cls.new_server(scheme)
        Client = type(Scheme.__name__, (DummyClientMixin, Scheme, Scheme.Client), {"_server":server})
        return Client(server, *args, **xargs)

    @classmethod
    def new_server(cls, scheme, *args, **xargs):
        Scheme = get_scheme(scheme)
        return Scheme.new_dummyserver(*args, **xargs)


class PlainEmulate(SchemeType):
    """ Emulator without network connection. Only internal variables are being used. """
    title = "Plain Emulator"
    description = "Emulator that skips network"
    client_args_help = ("SCHEME",)
    server_args_help = ("SCHEME",)

    @classmethod
    def new_client(cls, scheme, *args, **xargs):
        Client = type("Client", (PlainDummyClientMixin, get_scheme(scheme), AbstractClient), {})
        return Client(cls.new_server(scheme), *args, **xargs)

    @classmethod
    def new_server(cls, scheme, *args, **xargs):
        Scheme = get_scheme(scheme)
        return type("Server", (DummyServerMixin, Scheme, AbstractServer), {})(*args, **xargs)

