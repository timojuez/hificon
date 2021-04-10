import socket
from urllib.parse import urlparse
from ..core.util import ssdp
from ..core import AbstractScheme
from .. import Target


def check_target(host):
    uri = f"denon://{host}:23"
    try:
        with Target(uri) as target: name = target.name
    except (ConnectionError, socket.timeout, socket.gaierror, socket.herror, OSError):
        return False
    print("Found %s on %s."%(name, host))
    return uri


def discover_target():
    """
    Search local network for Denon amp
    """
    for response in ssdp.discover():
        if "denon" in response.st.lower() or "marantz" in response.st.lower():
            host = urlparse(response.location).hostname
            if uri := check_target(host): return uri
    raise Exception("No target found. Check if device is connected or set IP manually.")


class Auto(AbstractScheme):
    description = "Detect a supported server in network by using SSDP"
    client_args_help = tuple()

    def __new__(self, *args, **xargs):
        return Target(discover_target(), *args,**xargs)

