import argparse
from . import Target


def main():
    parser = argparse.ArgumentParser(description='Start a server for interacting in a given scheme')
    parser.add_argument('-t', '--target', metavar="URI", type=str, help='Target URI')
    parser.add_argument('--listen-host', metavar="HOST", type=str, help='Host (listening)')
    parser.add_argument('--listen-port', metavar="PORT", type=int, help='Port (listening)')
    parser.add_argument('--verbose', '-v', action='count', default=0, help='Verbose mode')
    args = parser.parse_args()
    xargs = {k:v for k,v in dict(listen_host=args.listen_host, listen_port=args.listen_port).items() if v}
    with Target(uri=args.target, role="server", verbose=args.verbose+1, **xargs) as server:
        while True: server.send(input())


if __name__ == "__main__":
    main()

