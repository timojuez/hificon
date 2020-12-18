"""
Dry software run that acts like a real amp
"""

import math
from decimal import Decimal
from ..amp import AbstractAmp, features
from .. import Amp_cls


default_values = dict(
    denon_name = "Dummy X7800H",
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


class DummyAmp:
    host = "emulator"
    name = "Emulator"
    
    def __init__(self, *args, **xargs):
        super().__init__(*args, **xargs)
        self.port = None

    def connect(self):
        AbstractAmp.connect(self)
        self.on_connect()

    def disconnect(self):
        AbstractAmp.disconnect(self)
        AbstractAmp.on_disconnected(self)

    def mainloop(self):
        if not self.connected: self.connect()
    
    def send(self, cmd):
        AbstractAmp.send(self, cmd)
        return self.query(cmd)

    def query(self, cmd, matches=None):
        r = None

        # cmd is a request
        for key, f in self.features.items():
            if f.call == cmd:
                encoded = get_val(f)
                self.on_receive_raw_data(encoded)
                if matches and matches(encoded) or f.matches(encoded):
                    if r is None: r = encoded
        if r is not None: return r

        # cmd is a command
        for key, f in self.features.items():
            if matches and matches(cmd) or f.matches(cmd):
                self.on_receive_raw_data(cmd)
                r = get_val(f)
                break
        return r


class Amp(AbstractAmp):
    protocol = "Emulator"

    def __new__(self, *args, emulate=".denon", **xargs):
        """ extra argument @emulate must be a protocol module """
        Original_amp = Amp_cls(protocol=emulate)
        return type("Amp",(DummyAmp,Original_amp,AbstractAmp),{})(*args, **xargs)
        
