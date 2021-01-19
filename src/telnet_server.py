import argparse, sys, time, selectors, traceback
from threading import Thread
from .amp import AbstractServer, AbstractClient
from .util.json_service import Service
from . import Server, Client


class ClientRepeater(AbstractServer):
    client = None
    
    def __init__(self, client, *args, **xargs):
        assert(isinstance(client, AbstractClient))
        self.client = client
        client.bind(on_receive_raw_data = lambda data:self.send(data))
        super().__init__(*args, **xargs)
    
    def enter(self, *args, **xargs): return self.client.enter(*args, **xargs)
    def exit(self, *args, **xargs): return self.client.exit(*args, **xargs)

    @property
    def prompt(self): return self.client.prompt
    
    def on_receive_raw_data(self, data): self.client.send(data)


class TelnetServer(Service):
    EVENTS = selectors.EVENT_READ | selectors.EVENT_WRITE
    
    def __init__(self, amp, listen_host, listen_port, linebreak="\r"):
        self._send = {}
        self.amp = amp
        self._break = linebreak
        print("Starting telnet amplifier")
        print(f"Operating on {self.amp.prompt}")
        print()
        self.amp.bind(send = self.on_amp_send)
        super().__init__(host=listen_host, port=listen_port, verbose=1)
        with self.amp:
            Thread(target=self.mainloop, daemon=True, name="mainloop").start()
            while True:
                cmd = input()
                self.on_amp_send(cmd)
    
    def connection(self, conn, mask):
        if conn not in self._send: self._send[conn] = b""
        return super().connection(conn, mask)

    def read(self, data):
        for data in data.strip().decode().replace("\n","\r").split("\r"):
            print("%s $ %s"%(self.amp.prompt,data))
            try: self.amp.on_receive_raw_data(data)
            except Exception as e: print(traceback.format_exc())
        
    def write(self, conn):
        time.sleep(.05)
        if not self._send[conn]: return
        l = len(self._send[conn])
        try: conn.sendall(self._send[conn][:l])
        except OSError: pass
        self._send[conn] = self._send[conn][l:]
    
    def on_amp_send(self, data):
        print(data)
        encoded = ("%s%s"%(data,self._break)).encode("ascii")
        # send to all connected listeners
        for conn in self._send: self._send[conn] += encoded


def main():
    parser = argparse.ArgumentParser(description='Start a telnet server for interacting on an amp instance')
    parser.add_argument('--listen-host', metavar="HOST", type=str, default="127.0.0.1", help='Host (listening)')
    parser.add_argument('--listen-port', metavar="PORT", type=int, default=0, help='Port (listening)')
    parser.add_argument('--protocol', type=str, default=None, help='Protocol')
    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument('--host', type=str, default=None, help='Repeat other amp')
    parser.add_argument('--port', type=int, default=None, help='Amp port')
    group.add_argument('-e', '--server', default=False, action="store_true", help='Server mode')
    parser.add_argument('-n', '--newline', action="store_true", help='Print \\n after each line (not native bahaviour)')
    parser.add_argument('--verbose', '-v', action='count', default=0, help='Verbose mode')
    args = parser.parse_args()
    xargs = dict(protocol=args.protocol, verbose=args.verbose)
    amp = Server(**xargs) if args.server \
        else ClientRepeater(Client(host=args.host, port=args.port, **xargs))
    TelnetServer(amp, args.listen_host, args.listen_port, "\n" if args.newline else "\r")


if __name__ == "__main__":
    main()

