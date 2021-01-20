import time, socket
from telnetlib import Telnet
from threading import Lock, Thread, Event
from contextlib import suppress
from .abstract_protocol import AbstractProtocol, AbstractClient


class TelnetClient(AbstractClient):
    """
    This class connects to the server via LAN and executes commands
    @host is the server's hostname or IP.
    """
    pulse = ""
    _telnet = None
    _send_lock = None
    _pulse_stop = None
    
    def __init__(self, *args, **xargs):
        super().__init__(*args, **xargs)
        self._send_lock = Lock()
        self._pulse_stop = Event()

    def send(self, cmd):
        super().send(cmd)
        try:
            with self._send_lock:
                assert(self.connected and self._telnet.sock)
                self._telnet.write(("%s\r"%cmd).encode("ascii"))
                time.sleep(.01)
        except (OSError, EOFError, AssertionError, AttributeError) as e:
            self.on_disconnected()
            raise BrokenPipeError(e)
        
    def read(self, timeout=None):
        try:
            assert(self.connected and self._telnet.sock)
            return self._telnet.read_until(b"\r",timeout=timeout).strip().decode()
        except socket.timeout: return None
        except (OSError, EOFError, AssertionError, AttributeError) as e:
            self.on_disconnected()
            raise BrokenPipeError(e)
    
    def connect(self):
        super().connect()
        if self.connected: return
        try: self._telnet = Telnet(self.host,self.port,timeout=2)
        except (ConnectionError, socket.timeout, socket.gaierror, socket.herror, OSError) as e:
            raise ConnectionError(e)
        else: self.on_connect()

    def disconnect(self):
        super().disconnect()
        with suppress(AttributeError, OSError):
            self._telnet.sock.shutdown(socket.SHUT_WR) # break read()
            self._telnet.close()
    
    def on_connect(self):
        super().on_connect()
        def func():
            while not self._pulse_stop.wait(10): self.send(self.pulse)
        self._pulse_stop.clear()
        if self.pulse is not None: Thread(target=func, daemon=True, name="pulse").start()
        
    def on_disconnected(self):
        super().on_disconnected()
        self._pulse_stop.set()
        
    def mainloop_hook(self):
        super().mainloop_hook()
        if self.connected:
            try: data = self.read(5)
            except ConnectionError: pass
            else:
                if data: self.on_receive_raw_data(data)
        else:
            try: self.connect()
            except ConnectionError: return self._stoploop.wait(3)


class AbstractTelnetProtocol(AbstractProtocol):
    #Server = None
    Client = TelnetClient


