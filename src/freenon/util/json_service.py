"""
The JsonService can be used for interprocess communication. It receives dicts.
The function "send" sends dicts.
"""

import selectors, socket, json, sys
from threading import Thread


PORT=654321


class JsonService(object):

    def __init__(self, host="127.0.0.1", port=PORT):
        print("[%s] start"%self.__class__.__name__, file=sys.stderr)
        self.sel = selectors.DefaultSelector()
        sock = socket.socket()
        sock.bind((host, port))
        sock.listen(100)
        sock.setblocking(False)
        self.sel.register(sock, selectors.EVENT_READ, self.accept)

    def __call__(self):
        Thread(target=self.mainloop, name=self.__class__.__name__, daemon=True).start()
        
    def mainloop(self):
        while True:
            events = self.sel.select()
            for key, mask in events:
                callback = key.data
                callback(key.fileobj, mask)

    def accept(self, sock, mask):
        conn, addr = sock.accept()
        conn.setblocking(False)
        self.sel.register(conn, selectors.EVENT_READ, self.read)

    def read(self, conn, mask):
        data = conn.recv(1000)
        if data:
            try:
                d = json.loads(data.decode())
                print("[%s] Received %s"%(self.__class__.__name__,d), file=sys.stderr)
            except Exception as e: print(repr(e))
            else: self.on_read(d)
        else:
            self.sel.unregister(conn)
            conn.close()

    def on_read(self, data): pass
    

def send(obj, port=PORT):
    sock = socket.socket()
    sock.connect_ex(("localhost", port))
    sock.send(json.dumps(obj).encode())

