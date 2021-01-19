import importlib

NAME = "HiFiCon"
PKG_NAME = "hificon"
VERSION = "1.10.0a"
AUTHOR = "Timo L. Richter"
URL = 'https://github.com/timojuez/hificon'
COPYRIGHT = ("Copyright \xa9 2021 %s\n"
    "Icons based on Ubuntu Mono Dark (GNU GPLv3)")%AUTHOR


def Amp_cls(protocol=None, cls="Amp"):
    """ returns amp instance from @protocol module. Read @protocol from config if None """
    from .amp import AmpType
    from .common.config import config
    protocol = protocol or config.get("Connection","protocol")
    try:
        module = importlib.import_module(protocol, "%s.protocol"%__name__)
    except ImportError:
        raise ValueError("Amp protocol `%s` not found."%protocol)
    Protocol = getattr(module, cls)
    assert(issubclass(Protocol, AmpType))
    return Protocol


class Client:

    def __new__(cls, *args, protocol=None, **xargs):
        """ returns amp instance from @protocol module. Read @protocol from config if None """
        Protocol = Amp_cls(protocol=protocol)
        Client = type("Client", (cls, Protocol, Protocol.Client), {})
        return Protocol.__new__(Client)
    
    def __init__(self, *args, protocol=None, **xargs): super().__init__(*args, **xargs)


class Server:

    def __new__(cls, *args, protocol=None, **xargs):
        """ returns amp instance from @protocol module. Read @protocol from config if None """
        Protocol = Amp_cls(protocol=protocol)
        Server = type("Server", (cls, Protocol, Protocol.Server), {})
        return Protocol.__new__(Server)
    
    def __init__(self, *args, protocol=None, **xargs): super().__init__(*args, **xargs)


class DummyServer(DummyServer, Server): pass


Amp = Client

