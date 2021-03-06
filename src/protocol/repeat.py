from ..core.transport import ProtocolType
from .. import Target


class ClientRepeaterMixin:
    _client = None
    
    def __init__(self, target, *args, **xargs):
        self._client = target
        self._client.bind(on_receive_raw_data = lambda data:self.send(data))
        super().__init__(*args, **xargs)
    
    def enter(self):
        super().enter()
        self._client.enter()

    def exit(self):
        super().exit()
        self._client.exit()

    @property
    def prompt(self): return self._client.prompt
    
    def on_receive_raw_data(self, data): self._client.send(data)


class Repeat(ProtocolType):
    protocol = "Repeater"
    uri_server = ":CLIENT_URI"
    description = "A server that connects to another server and repeats the data"

    @classmethod
    def new_client(cls, protocol, *args, **xargs): raise NotImplementedError()

    @classmethod
    def new_server(cls, *args, **xargs):
        target = Target(":".join(args), **xargs)
        return type("Server", (ClientRepeaterMixin, target.Server), {})(target)

