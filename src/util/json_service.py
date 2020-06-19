"""
The JsonService can be used for interprocess communication. It receives dicts.
The function "send" sends dicts.
"""

import selectors, socket, json, sys
from threading import Thread


PORT=654321


class JsonService(object):
    """
    A service communicating with Json objects. Call mainloop() after init.
    """

    def __init__(self, host="127.0.0.1", port=PORT, verbose=0):
        self._verbose = verbose
        if self._verbose > 0: print(
            "[%s] Listening on port %d"%(self.__class__.__name__,port), file=sys.stderr)
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
                if self._verbose > 1: print(
                    "[%s] Received %s"%(self.__class__.__name__,d), file=sys.stderr)
            except Exception as e: print(repr(e))
            else: self.on_read(d)
        else:
            self.sel.unregister(conn)
            conn.close()

    def on_read(self, data): pass


class RemoteControlService(JsonService):
    """ 
    Opens a service on a port and executes calls on @obj when received 
    message schema: {"func": property_of_obj, "kwargs": {}}
    """

    def __init__(self, obj, func_whitelist=None, *args, **xargs):
        self._obj = obj
        self._func_whitelist = func_whitelist
        super().__init__(*args,**xargs)
        
    def on_read(self, data):
        try:
            if self._func_whitelist: assert(data["func"] in self._func_whitelist)
            #assert(isinstance(data["kwargs"]["button"],bool))
            func = getattr(self._obj, data["func"])
            kwargs = data["kwargs"]
        except:
            return print("[%s] invalid message."%self.__class__.__name__, file=sys.stderr)
        Thread(name=self._obj.__class__.__name__, target=func,kwargs=kwargs, 
            daemon=True).start()
            

def send(obj, port=PORT):
    sock = socket.socket()
    sock.connect_ex(("localhost", port))
    sock.send(json.dumps(obj).encode())

