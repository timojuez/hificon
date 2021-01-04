"""
Dry software run that acts like a real amp
"""

import math
from decimal import Decimal
from ..amp import AbstractAmp, features
from .. import Amp_cls


default_values = dict(
    name = "Dummy X7800H",
)


def get_val(f):
    if f.isset(): val = f.get()
    elif f.key in default_values: val = default_values[f.key]
    elif getattr(f, "default_value", None): val = f.default_value
    elif isinstance(f, features.IntFeature): val = math.ceil((f.max+f.min)/2)
    elif isinstance(f, features.DecimalFeature): val = Decimal(f.max+f.min)/2
    elif isinstance(f, features.SelectFeature): val = f.options[0] if f.options else "?"
    elif isinstance(f, features.BoolFeature): val = False
    else: raise TypeError("Feature type %s not known."%f)
    return f.encode(val)


class DummyAmp:
    host = "emulator"
    
    def __init__(self, *args, **xargs):
        super().__init__(*args, **xargs)
        self.port = None

    def connect(self):
        AbstractAmp.connect(self)
        self.on_connect()

    def disconnect(self):
        AbstractAmp.disconnect(self)

    def mainloop(self):
        if not self.connected: self.connect()
    
    def send(self, cmd):
        AbstractAmp.send(self, cmd)
        if not self.connected: raise BrokenPipeError("Not connected")
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

    def __new__(self, *args, emulate=None, **xargs):
        """ extra argument @emulate must be a protocol module """
        Original_amp = Amp_cls(protocol=emulate)
        if issubclass(Original_amp, Amp): # do not emulate Emulator and avoid RecursionError
            Original_amp = Amp_cls(protocol=".denon")
        return type("Amp",(DummyAmp,Original_amp,AbstractAmp),{})(*args, **xargs)
        
