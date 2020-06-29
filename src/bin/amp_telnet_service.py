import argparse, sys, time, selectors, traceback
from ..util.json_service import Service
from .. import Amp


class Main(Service):
    """
    A service communicating with Json objects. Call mainloop() after init.
    """
    EVENTS = selectors.EVENT_READ | selectors.EVENT_WRITE
    
    def __init__(self):
        parser = argparse.ArgumentParser(description='Start a telnet server for interacting on an amp')
        parser.add_argument('--host', type=str, default="127.0.0.1", help='Listen')
        parser.add_argument('--port', type=int, default=0, help='Listen')
        parser.add_argument('--protocol', type=str, default=".dummy", help='Amp protocol')
        parser.add_argument('-n','--newline', action="store_true", help='Print \\n after each line (not native bahaviour)')
        self.args = parser.parse_args()
        self._send = b""
        self._break = "\n" if self.args.newline else "\r"
        self.amp = Amp(protocol=self.args.protocol, verbose=2)
        self.amp.bind(on_receive_raw_data = self.on_amp_read)
        super().__init__(host=self.args.host, port=self.args.port, verbose=1)
        self.mainloop()

    def read(self, data):
        try: self.amp.send(data.strip().decode())
        except Exception as e: print(traceback.format_exc())
        
    def write(self, conn):
        time.sleep(.1)
        if not self._send: return
        l = len(self._send)
        try: conn.sendall(self._send[:l])
        except OSError: pass
        self._send = self._send[l:]
    
    def on_amp_read(self, data):
        self._send += ("%s%s"%(data,self._break)).encode("ascii")


main = lambda:Main()
if __name__ == "__main__":
    main()

