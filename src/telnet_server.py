import argparse, sys
from .common import AbstractServer, AbstractClient, TelnetServer
from . import Server, DummyServer, Client


class ClientRepeater(TelnetServer):
    client = None
    
    def __init__(self, listen_host, listen_port, linebreak, *args, **xargs):
        self.client = Client(*args, **xargs)
        self.client.bind(on_receive_raw_data = lambda data:self.send(data))
        super().__init__(listen_host, listen_port, linebreak)
    
    def enter(self, *args, **xargs): return self.client.enter(*args, **xargs)
    def exit(self, *args, **xargs): return self.client.exit(*args, **xargs)

    @property
    def prompt(self): return self.client.prompt
    
    def on_receive_raw_data(self, data): self.client.send(data)


def main():
    parser = argparse.ArgumentParser(description='Start a server for interacting on a given protocol')
    parser.add_argument('--listen-host', metavar="HOST", type=str, default="127.0.0.1", help='Host (listening)')
    parser.add_argument('--listen-port', metavar="PORT", type=int, default=0, help='Port (listening)')
    parser.add_argument('--protocol', type=str, default=None, help='Protocol')
    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument('-e', '--emulate', default=Server, const=DummyServer, dest="server",
        action="store_const", help='Emulate server (dry run)')
    group.add_argument('-r', '--repeat', action="store_true", help='Repeat another server')
    
    parser.add_argument('--host', type=str, default=None, help='Server to repeat')
    parser.add_argument('--port', type=int, default=None, help='Server port')
    parser.add_argument('-n', '--newline', action="store_const", default="\r", const="\n", help='Print \\n after each line (not native bahaviour)')
    parser.add_argument('--verbose', '-v', action='count', default=0, help='Verbose mode')
    args = parser.parse_args()
    xargs = dict(protocol=args.protocol, listen_host=args.listen_host, listen_port=args.listen_port, linebreak=args.newline, verbose=args.verbose)
    if args.repeat: ClientRepeater(host=args.host, port=args.port, **xargs)
    else: args.server(**xargs)


if __name__ == "__main__":
    main()

