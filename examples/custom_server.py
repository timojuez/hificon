"""
This shows how to share values from ExternalEntity with clients in a client-server architecture.

Run server:
    examples$ python3 -m hificon.server -t custom_server.MyScheme://127.0.0.1:1234:900
Run client:
    examples$ python3 -m hificon.hifish -t custom_server.MyScheme://127.0.0.1:1234
    The value $counter shall always be synchronised with the server.
"""

import time
from threading import Thread
from hificon.core.transport.telnet import TelnetServer, TelnetScheme
from hificon.amp import TelnetAmp
from hificon.core.transport import features


class ExternalEntity:
    """ This just increases numbers independently. Let's assume this is only possible on the server. """
    value = 0

    def __init__(self, target, start):
        self.target = target
        self.value = start
        Thread(target=self.count, daemon=True).start()

    def count(self):
        while True:
            self.value = (self.value+1)%50
            self.target.counter = self.value # sync clients
            time.sleep(1)

    def set(self, value):
        """ call caused by client """
        if value < 50:
            self.value = value
            self.target.counter = self.value # sync clients


class MyServer(TelnetServer):
    """ Adds a custom value START_COUNT to init and changes the URI to
    SCHEME://IP:PORT:START_COUNT
    init initiates the connection to ExternalEntity
    """
    init_args_help = ("//LISTEN_IP", "LISTEN_PORT", "START_COUNT")
    external_entity = None
    
    def __init__(self, ip="127.0.0.1", port=0, start=0, *args, **xargs):
        super().__init__(ip, port, *args, **xargs)
        self.external_entity = ExternalEntity(self, int(start))


class MyScheme(TelnetScheme):
    """ must have the reference to MyServer.
    If this represents an amplifier, you can inherit from TelnetAmp instead of TelnetScheme. """
    description = "My custom scheme"
    Server = MyServer


@MyScheme.add_feature
class Counter(features.IntFeature):
    min = 0
    max = 50
    call = "get counter"
    
    def serialize(self, value): return "set counter %d"%value
    def unserialize(self, data): return int(data.rsplit(" ",1)[1])
    def matches(self, data): return data.startswith("set counter")
    def set_on_server(self, value): self.target.external_entity.set(value)
    def poll_on_server(self): self.set(self.target.external_entity.value)

