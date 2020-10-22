"""
Dry software run that acts like a real amp
"""

import math
from ..amp import AbstractAmp, features, make_amp
from .. import Amp_cls


default_values = dict(
    volume = 25.5,
    maxvol = 98,
    denon_name = "Dummy X7800H",
    muted = False,
)


class DummyAmp:
    host = "dummy"
    name = "Emulator"
    connected = True
    
    def __init__(self, *args, **xargs):
        super().__init__(*args, **xargs)
        self.protocol = "%s_emulator"%super().protocol
        self.port = None
        for name, f in self.features.items():
            if name in default_values: val = default_values[name]
            elif isinstance(f, features.IntFeature): val = math.ceil((f.max+f.min)/2)
            elif isinstance(f, features.FloatFeature): val = (f.max+f.min)/2
            elif isinstance(f, features.SelectFeature) and f.options: val = f.options[0]
            elif isinstance(f, features.BoolFeature): val = True
            else: continue
            f.store(val)
    
    def connect(self): return AbstractAmp.connect(self)

    def disconnect(self):
        AbstractAmp.disconnect(self)
        AbstractAmp.on_disconnected(self)

    def mainloop(self): pass
    
    def send(self, cmd): return self.query(cmd)

    def query(self, cmd, matches=None):
        r = None

        # cmd is a request
        for attr, f in self.features.items():
            if f.call == cmd:
                if not f.isset():
                    print("WARNING: `%s` is being requested but has not been set."%f.name)
                    return
                encoded = f.encode(f.get())
                self.on_receive_raw_data(encoded)
                if matches and matches(encoded) or f.matches(encoded):
                    if r is None: r = encoded
        if r is not None: return r

        # cmd is a command
        for attr, f in self.features.items():
            if matches and matches(cmd) or f.matches(cmd):
                self.on_receive_raw_data(cmd)
                encoded = f.encode(f.get())
                r = encoded
                break
        return r
    

def Amp(*args, emulate=None, **xargs):
    """ extra argument @emulate must be a protocol module """
    Original_amp = Amp_cls(protocol=emulate)
    return type("Amp",(DummyAmp,Original_amp,AbstractAmp),{})(*args, **xargs)

