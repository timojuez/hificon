"""
Dry software run that acts like a real amp
"""

import math, time
from decimal import Decimal
from threading import Timer, Event
from ..amp import AbstractAmp, features
from .. import Amp_cls


default_values = dict(
    name = "Dummy X7800H",
    muted = False,
    source_names = " END",
)


def get_val(f):
    if f.isset(): val = f.get()
    elif f.key in default_values: val = default_values[f.key]
    elif getattr(f, "default_value", None): val = f.default_value
    elif isinstance(f, features.IntFeature): val = math.ceil((f.max+f.min)/2)
    elif isinstance(f, features.DecimalFeature): val = Decimal(f.max+f.min)/2
    elif isinstance(f, features.SelectFeature): val = f.options[0] if f.options else "?"
    elif isinstance(f, features.BoolFeature): val = True
    else: raise TypeError("Feature type %s not known."%f)
    return f.encode(val)


def mainloop(func):
    def dec(self, *args, **xargs):
        self._tasks.append((func, (self,)+args, xargs))
        self._continue_mainloop.set()
    return dec
    

class DummyAmp:
    host = "emulator"
    _continue_mainloop = Event
    _tasks = list
    
    def __init__(self, *args, **xargs):
        super().__init__(*args, **xargs)
        self.port = None
        self._continue_mainloop = self._continue_mainloop()
        self._tasks = self._tasks()

    def connect(self):
        time.sleep(.05)
        AbstractAmp.connect(self)
        self.on_connect()

    def disconnect(self):
        AbstractAmp.disconnect(self)
        self._continue_mainloop.set()
        self.on_disconnected()

    def mainloop_hook(self):
        AbstractAmp.mainloop_hook(self)
        if not self.connected: self.connect()
        while self._tasks:
            func, args, xargs = self._tasks.pop(0)
            func(*args, **xargs)
        if self._continue_mainloop.wait(9): self._continue_mainloop.clear()
    
    @mainloop
    def send(self, cmd):
        AbstractAmp.send(self, cmd)
        if not self.connected: raise BrokenPipeError("Not connected")
        time.sleep(.01)
        Timer(0.05, lambda cmd=cmd: self._receive_dummy_answer(cmd)).start()

    @mainloop
    def _receive_dummy_answer(self, cmd):
        called_features = [f for key, f in self.features.items() if f.call == cmd]
        
        if called_features:
            # cmd is a request
            for f in called_features:
                encoded = get_val(f)
                self.on_receive_raw_data(encoded)
        else:
            # cmd is a command
            for key, f in self.features.items():
                if f.matches(cmd):
                    self.on_receive_raw_data(cmd)
                    break


class Amp(AbstractAmp):
    protocol = "Emulator"

    def __new__(self, *args, emulate=".denon", **xargs):
        """ extra argument @emulate must be a protocol module """
        Original_amp = Amp_cls(protocol=emulate)
        return type("Amp",(DummyAmp,Original_amp,AbstractAmp),{})(*args, **xargs)
        
