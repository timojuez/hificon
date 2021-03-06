from ..core.transport import ProtocolType
from .denon import Denon
from .emulate import Emulate
from .emulate import PlainEmulate
from .raw_telnet import RawTelnet
from .auto import Auto
from .repeat import Repeat

protocols = {cls.protocol:cls for name, cls in globals().items()
    if type(cls)==type and issubclass(cls, ProtocolType) and cls != ProtocolType}

