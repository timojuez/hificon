from decimal import Decimal
from hificon.amp import TelnetAmp
from hificon.core.transmission import features


class MyTelnetScheme(TelnetAmp):
    """ try by running `examples$ python3 -m hificon.hifish -t emulate:my_scheme.MyTelnetScheme`
    or start the server by `examples$ python3 -m hificon.server -t my_scheme.MyTelnetScheme://127.0.0.1:1234`
    and start the client by `examples$ python3 -m hificon.hifish -t my_scheme.MyTelnetScheme://127.0.0.1:1234`
    """
    description = "My custom scheme"


@MyTelnetScheme.add_feature(overwrite=True)
class Power(features.BoolFeature):
    call = "?pwr"

    def serialize(self, value): return "!pwr=1" if value else "!pwr=0"
    def unserialize(self, data): return data == "!pwr=1"
    def matches(self, data): return data.startswith("!pwr")
    def poll_on_server(self): self.set(True)
    def set_on_server(self, value): self.set(value)


@MyTelnetScheme.add_feature
class Value(features.DecimalFeature):
    min = 0
    max = 10
    call = "get value"
    
    def serialize(self, value): return "set value %0.2f"%value
    def unserialize(self, data): return Decimal(data.rsplit(" ",1)[1])
    def matches(self, data): return data.startswith("set value")
    def set_on_server(self, value): self.set(value)
    def poll_on_server(self): self.set(5)

