import argparse, sys
from .core import AbstractServer, AbstractClient, TelnetServer
from . import Target


class ClientRepeater(TelnetServer):
    client = None
    
    def __init__(self, listen_host, listen_port, linebreak, *args, **xargs):
        self.client = Target(*args, role="client", **xargs)
        self.client.bind(on_receive_raw_data = lambda data:self.send(data))
        super().__init__(listen_host, listen_port, linebreak)
    
    def enter(self):
        super().enter()
        self.client.enter()

    def exit(self):
        super().exit()
        self.client.exit()

    @property
    def prompt(self): return self.client.prompt
    
    def on_receive_raw_data(self, data): self.client.send(data)


def main():
    parser = argparse.ArgumentParser(description='Start a server for interacting on a given protocol')
    parser.add_argument('--listen-host', metavar="HOST", type=str, default="127.0.0.1", help='Host (listening)')
    parser.add_argument('--listen-port', metavar="PORT", type=int, default=0, help='Port (listening)')
    parser.add_argument('--target', metavar="URI", type=str, default=None, help='Target URI')
    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument('-e', '--emulate', default="server", const="dummyserver", dest="role",
        action="store_const", help='Emulate server (dry run)')
    group.add_argument('-r', '--repeat', action="store_true", help='Repeat target')
    
    parser.add_argument('-n', '--newline', action="store_const", default="\r", const="\n", help='Print \\n after each line (not native bahaviour)')
    parser.add_argument('--verbose', '-v', action='count', default=0, help='Verbose mode')
    args = parser.parse_args()
    xargs = dict(uri=args.target, listen_host=args.listen_host, listen_port=args.listen_port, linebreak=args.newline, verbose=args.verbose+1)
    if args.repeat: server = ClientRepeater(**xargs)
    else: server = Target(role=args.role, **xargs)
    with server:
        while True: server.send(input())


if __name__ == "__main__":
    main()

