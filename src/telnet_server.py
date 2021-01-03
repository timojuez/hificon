import argparse, sys, time, selectors, traceback
from threading import Thread
from .util.json_service import Service
from . import Amp


class Main(Service):
    EVENTS = selectors.EVENT_READ | selectors.EVENT_WRITE
    
    def __init__(self):
        parser = argparse.ArgumentParser(description='Start a telnet server for interacting on an amp instance')
        parser.add_argument('--listen-host', metavar="HOST", type=str, default="127.0.0.1", help='Host (listening)')
        parser.add_argument('--listen-port', metavar="PORT", type=int, default=0, help='Port (listening)')
        parser.add_argument('--protocol', type=str, default=None, help='Amp protocol')
        parser.add_argument('--host', type=str, default=None, help='Amp host')
        parser.add_argument('--port', type=int, default=None, help='Amp port')
        parser.add_argument('-e', '--emulate', default=False, action="store_true", help='Use emulator (dry run)')
        parser.add_argument('-n', '--newline', action="store_true", help='Print \\n after each line (not native bahaviour)')
        parser.add_argument('--verbose', '-v', action='count', default=0, help='Verbose mode')
        self.args = parser.parse_args()
        self._send = {}
        self._break = "\n" if self.args.newline else "\r"
        if self.args.emulate: ampargs = {"protocol": ".emulator", "emulate": self.args.protocol}
        else: ampargs = {"protocol": self.args.protocol}
        self.amp = Amp(host=self.args.host, port=self.args.port, verbose=self.args.verbose, **ampargs)
        print("Starting telnet amplifier")
        print(f"Operating on {self.amp.prompt}")
        print()
        self.amp.bind(on_receive_raw_data = self.on_amp_read)
        super().__init__(host=self.args.listen_host, port=self.args.listen_port, verbose=1)
        with self.amp:
            Thread(target=self.mainloop, daemon=True, name="mainloop").start()
            while True:
                cmd = input()
                self.on_amp_read(cmd)
    
    def connection(self, conn, mask):
        if conn not in self._send: self._send[conn] = b""
        return super().connection(conn, mask)

    def read(self, data):
        for data in data.strip().decode().replace("\n","\r").split("\r"):
            print("%s $ %s"%(self.amp.prompt,data))
            try: self.amp.send(data)
            except Exception as e: print(traceback.format_exc())
        
    def write(self, conn):
        time.sleep(.05)
        if not self._send[conn]: return
        l = len(self._send[conn])
        try: conn.sendall(self._send[conn][:l])
        except OSError: pass
        self._send[conn] = self._send[conn][l:]
    
    def on_amp_read(self, data):
        print(data)
        encoded = ("%s%s"%(data,self._break)).encode("ascii")
        # send to all connected listeners
        for conn in self._send: self._send[conn] += encoded


main = lambda:Main()
if __name__ == "__main__":
    main()

