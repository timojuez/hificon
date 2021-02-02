import socket
from urllib.parse import urlparse
from ..core.util import ssdp
from .. import Target


def check_amp(host):
    uri = f"denon://{host}:23"
    try:
        with Target(uri) as amp: name = amp.name
    except (ConnectionError, socket.timeout, socket.gaierror, socket.herror, OSError):
        return False
    print("Found %s on %s."%(name, host))
    return uri


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

