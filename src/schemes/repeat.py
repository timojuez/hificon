from ..core.transport import SchemeType
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
        self.uri = f"{self.scheme}:{self._client.uri}"

    def exit(self):
        super().exit()
        self._client.exit()

    def on_receive_raw_data(self, data):
        try: self._client.send(data)
        except ConnectionError as e: print(repr(e))


class Repeat(SchemeType):
    title = "Repeater"
    description = "A server that connects to another server and repeats the data"
    server_args_help = ("CLIENT_URI",)

    @classmethod
    def new_client(cls, scheme, *args, **xargs): raise NotImplementedError()

    @classmethod
    def new_server(cls, *args, **xargs):
        target = Target(":".join(args), connect=False)
        return type("Server", (ClientRepeaterMixin, target.Server, cls), {})(target, **xargs)

