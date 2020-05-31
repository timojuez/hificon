#!/usr/bin/env python3
# -*- coding: utf-8 -*- 

import selectors, socket, json, sys
from .volume_changer import VolumeChanger


PORT=1234 # TODO


class JsonService(object):

    def __init__(self, host="localhost", port=PORT):
        print("[%s] start"%self.__class__.__name__, file=sys.stderr)
        self.sel = selectors.DefaultSelector()
        sock = socket.socket()
        sock.bind((host, port))
        sock.listen(100)
        sock.setblocking(False)
        self.sel.register(sock, selectors.EVENT_READ, self.accept)

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
            except e: print(repr(e))
            else: self.on_read(d)
        else:
            self.sel.unregister(conn)
            conn.close()

    def on_read(self, data): pass
    

def send(obj, port=PORT):
    sock = socket.socket()
    sock.connect_ex(("localhost", port))
    sock.send(json.dumps(obj).encode())


class VolumeService(JsonService):

    def __init__(self):
        print("Key Binding Service")
        self.vc = VolumeChanger()
        super().__init__()
        
    def on_read(self, data):
        if data["func"] not in ("press","release") or not isinstance(data["button"],bool):
            return print("[%s] invalid message."%self.__class__.__name__, file=sys.stderr)
        getattr(self.vc, data["func"])(data["button"])
        

def main():
    VolumeService().mainloop()
    
if __name__ == "__main__":
    main()

