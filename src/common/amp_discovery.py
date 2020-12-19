import socket
from urllib.parse import urlparse
from ..util import ssdp
from .. import Amp


def check_amp(host):
    try:
        with Amp(protocol=".denon", host=host, port=23) as amp:
            name = amp.denon_name
    except (ConnectionError, socket.timeout, socket.gaierror, socket.herror, OSError):
        return False
    print("Found %s on %s."%(name, host))
    return dict(host=host,port=23,name=name,protocol=".denon")


def discover_amp():
    """
    Search local network for Denon amp
    """
    for response in ssdp.discover():
        if "denon" in response.st.lower() or "marantz" in response.st.lower():
            host = urlparse(response.location).hostname
            if amp_details := check_amp(host): return amp_details
    raise Exception("No Denon amp found. Check if amp is connected or"
        " set IP manually.")

