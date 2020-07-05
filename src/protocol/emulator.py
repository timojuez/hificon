"""
Dry software run that acts like a real amp
"""

from ..amp import AbstractAmp, make_amp
from .. import Amp_cls


default_values = dict(
    volume = 25.5,
    maxvol = 98,
    power = True,
    denon_name = "Dummy X7800H",
    source = "CBL/Any",
    sub_volume = 50,
    muted = False,
)


class DummyAmp:
    host = "dummy"
    name = "Emulator"
    connected = True
    
    def __init__(self, *args, **xargs):
        super().__init__(*args, **xargs)
        self.protocol = "%s_emulator"%super().protocol
        for attr, value in default_values.items():
            if attr in self.features: self.features[attr].store(value)
    
    def connect(self): return AbstractAmp.connect(self)

    def disconnect(self):
        AbstractAmp.disconnect(self)
        AbstractAmp.on_disconnected(self)

    def mainloop(self): pass
    
    def send(self, cmd): return self.query(cmd)

    def query(self, cmd, matches=None):
        r = None
        for attr, f in self.features.items():
            if f.call == cmd:
                encoded = f.encode(f.get())
                self.on_receive_raw_data(encoded)
                if matches and matches(encoded) or f.matches(encoded):
                    if r is None: r = encoded
        if r is not None: return r
        for attr, f in self.features.items():
            if matches and matches(cmd) or f.matches(cmd):
                f.consume(cmd)
                encoded = f.encode(f.get())
                self.on_receive_raw_data(encoded)
                r = encoded
        return r
    

def Amp(*args, emulate=None, **xargs):
    """ extra argument @emulate must be a protocol module """
    Original_amp = Amp_cls(protocol=emulate)
    return type("Amp",(DummyAmp,Original_amp,AbstractAmp),{})(*args, **xargs)

