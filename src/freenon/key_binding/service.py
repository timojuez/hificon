#!/usr/bin/env python3
# -*- coding: utf-8 -*- 

import selectors, socket, json, sys
from .volume_changer import VolumeChanger

PORT=1234 # TODO


class Service(object):

    def __init__(self):
        print("[%s] start"%self.__class__.__name__, file=sys.stderr)
        self.sel = selectors.DefaultSelector()
        sock = socket.socket()
        sock.bind(('localhost', PORT))
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
        conn, addr = sock.accept()  # Should be ready
        #print('accepted', conn, 'from', addr)
        conn.setblocking(False)
        self.sel.register(conn, selectors.EVENT_READ, self.read)

    def read(self, conn, mask):
        data = conn.recv(1000)  # Should be ready
        if data:
            #print('read', repr(data))
            try:
                d = json.loads(data.decode())
                print("[%s] Received %s"%(self.__class__.__name__,d))
            except e: print(repr(e))
            else: self.on_read(d)
        else:
            #print('closing', conn)
            self.sel.unregister(conn)
            conn.close()

    def on_read(self, data): pass
    

def send(obj):
    sock = socket.socket()
    sock.connect_ex(("localhost",PORT))
    sock.send(json.dumps(obj).encode())


class VolumeService(Service):

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

