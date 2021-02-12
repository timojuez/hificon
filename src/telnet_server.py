import argparse
from . import Target


class ClientRepeaterMixin:
    client = None
    
    def __init__(self, target, *args, **xargs):
        self.client = target
        self.client.bind(on_receive_raw_data = lambda data:self.send(data))
        super().__init__(*args, **xargs)
    
    def enter(self):
        super().enter()
        self.client.enter()

    def exit(self):
        super().exit()
        self.client.exit()

    @property
    def prompt(self): return self.client.prompt
    
    def on_receive_raw_data(self, data): self.client.send(data)


def create_client_repeater(*args, kwargs_server={}, **xargs):
    target = Target(*args, **xargs)
    return type("Server", (ClientRepeaterMixin, target.Server), {})(target, **kwargs_server)


def main():
    parser = argparse.ArgumentParser(description='Start a server for interacting on a given protocol')
    parser.add_argument('--listen-host', metavar="HOST", type=str, default="127.0.0.1", help='Host (listening)')
    parser.add_argument('--listen-port', metavar="PORT", type=int, default=0, help='Port (listening)')
    parser.add_argument('-t', '--target', metavar="URI", type=str, default=None, help='Target URI')
    parser.add_argument('-r', '--repeat', action="store_true", help='Repeat target')
    parser.add_argument('--verbose', '-v', action='count', default=0, help='Verbose mode')
    args = parser.parse_args()
    xargs = dict(listen_host=args.listen_host, listen_port=args.listen_port, verbose=args.verbose+1)
    if args.repeat: server = create_client_repeater(uri=args.target, kwargs_server=xargs)
    else: server = Target(uri=args.target, role="server", **xargs)
    with server:
        while True: server.send(input())


if __name__ == "__main__":
    main()

