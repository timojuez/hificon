"""
Dry software run that acts like a real amp
"""

import math
from decimal import Decimal
from ..amp import AbstractProtocol, AbstractServer, AbstractClient, features
from .. import Amp_cls


default_values = dict(
    name = "Dummy X7800H",
)


class DummyServer:
    
    def poll_feature(self, f, *args, **xargs):
        if f.isset(): val = f.get()
        elif f.key in default_values: val = default_values[f.key]
        elif getattr(f, "default_value", None): val = f.default_value
        elif isinstance(f, features.IntFeature): val = math.ceil((f.max+f.min)/2)
        elif isinstance(f, features.DecimalFeature): val = Decimal(f.max+f.min)/2
        elif isinstance(f, features.BoolFeature): val = False
        elif isinstance(f, features.SelectFeature): val = f.options[0] if f.options else "?"
        else: raise TypeError("Feature type %s not known."%f)
        f.store(val)


class ServerAdapterClient:
    """ This client class connects to an internal server instance """
    host = "emulator"
    _server = None
    
    def __init__(self, server, *args, **xargs):
        super().__init__(*args, **xargs)
        self.port = None
        self._server = server
        assert(isinstance(server, AbstractServer))
        server.bind(send = lambda data: self.on_receive_raw_data(data))

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
        return self._server.on_receive_raw_data(data)


class Amp(AbstractProtocol):
    protocol = "Emulator"

    def __new__(self, *args, emulate=None, **xargs):
        """ extra argument @emulate must be a protocol module """
        OriginalClass = Amp_cls(protocol=emulate)
        if issubclass(OriginalClass, Amp): # do not emulate Emulator and avoid RecursionError
            OriginalClass = Amp_cls(protocol=".denon")
        Server = type("Server",(DummyServer, OriginalClass, AbstractServer),{})
        Client = type("Client",(ServerAdapterClient, OriginalClass, AbstractClient), {})
        return Client(*args, server=Server(), **xargs)

