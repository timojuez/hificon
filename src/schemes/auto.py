import socket
from urllib.parse import urlparse
from ..core.util import ssdp
from ..core import AbstractScheme
from .. import Target, get_schemes


def check_target(target): return get_name(target) is not None

def get_name(target):
    try:
        with target: return target.name
    except (ConnectionError, socket.timeout, socket.gaierror, socket.herror, OSError): return


def discover_targets():
    """
    Search local network for supported devices and yield client instance
    """
    schemes = list(get_schemes())
    discovered_hosts = set()
    for response in ssdp.discover():
        host = urlparse(response.location).hostname
        if host in discovered_hosts: continue
        for Scheme in schemes:
            if target := Scheme.new_client_by_ssdp(response):
                discovered_hosts.add(host)
                yield target


def discover_target():
    """ guess server and return attached target instance """
    for target in discover_targets():
        if name := get_name(target):
            print("Found %s on %s."%(name, target.uri))
            return target
    raise Exception("No target found. Check if device is connected or configure manually.")


class Auto(AbstractScheme):
    description = "Detect a supported server in network by using SSDP"
    client_args_help = tuple()

    def __new__(self, *args, **xargs):
        return Target(discover_target().uri, *args, **xargs)

