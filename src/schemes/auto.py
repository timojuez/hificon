import socket
from urllib.parse import urlparse
from ..core.util import ssdp
from ..core import AbstractScheme
from .. import Target, get_schemes


def check_target(uri): return get_name(uri) is not None

def get_name(uri):
    try:
        with Target(uri) as target: name = target.name
    except (ConnectionError, socket.timeout, socket.gaierror, socket.herror, OSError): return
    print("Found %s on %s."%(name, uri))
    return name


def discover_targets():
    """
    Search local network for supported devices and yield uri, name
    """
    schemes = list(get_schemes())
    discovered_hosts = set()
    for response in ssdp.discover():
        host = urlparse(response.location).hostname
        port = 23 # TODO
        if host in discovered_hosts: continue
        for Scheme in schemes:
            if not Scheme.matches_ssdp_response(response): continue
            discovered_hosts.add(host)
            t = Target(Scheme.scheme, host, port)
            yield t.uri


def discover_target():
    """ guess amp and return uri """
    for uri in discover_targets():
        if check_target(uri): return uri
    raise Exception("No target found. Check if device is connected or set IP manually.")


class Auto(AbstractScheme):
    description = "Detect a supported server in network by using SSDP"
    client_args_help = tuple()

    def __new__(self, *args, **xargs):
        return Target(discover_target(), *args,**xargs)

