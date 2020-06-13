#!/usr/bin/env python3
# -*- coding: utf-8 -*- 

import subprocess, sys, ipaddress, os, argparse, pkgutil, socket
try: import nmap
except ImportError: pass
try: import netifaces
except ImportError: pass
from ..config import config, FILE


class Main(object):

    def __init__(self):
        parser = argparse.ArgumentParser(description='Freenon Setup Tool')
        discover = parser.add_mutually_exclusive_group()
        discover.add_argument('--discover', dest="nothing", action="store_false", help='Include Denon amp discovery (default)')
        discover.add_argument('--no-discover', default=DenonDiscoverer, dest="discover", action="store_false")

        keys = parser.add_mutually_exclusive_group()
        keys.add_argument('--keys', default=False, action="store_const", const=setup_xorg_key_binding, help='Setup Xorg mouse and keyboard volume keys binding for current user')
        keys.add_argument('--no-keys', action="store_false", help='(default)')

        source = parser.add_mutually_exclusive_group()
        source.add_argument('--source-setup', dest="nothing", action="store_false", help='Connect Denon amp source setting to computer (default)')
        source.add_argument('--no-source-setup', default=source_setup, dest="source_setup", action="store_false")
        
        port = parser.add_mutually_exclusive_group()
        port.add_argument('--set-port', dest="nothing", action="store_false", help='Set a port for inter process communication (default)')
        port.add_argument('--no-set-port', default=set_port, dest="set_port", action="store_false")
        
        parser.add_argument("-v",'--verbose', default=False, action='store_true', help='Verbose mode')
        self.args = parser.parse_args()
        
    def __call__(self):
        if os.path.exists(FILE) and input("This will modify `%s`. Proceed? [y/n] "%FILE) != "y": return
        config.clear_sections()
        config.read([FILE])
        for arg, func in filter(lambda e: callable(e[1]), self.args._get_kwargs()):
            try: func()
            except Exception as e:
                print("Exception in %s: %s"%(arg,repr(e)))
            print()
        config.save()
        print("done. The service needs to be (re)started.")
        

def set_port():
    sock = socket.socket()
    sock.bind(('127.0.0.1', 0))
    port = sock.getsockname()[1]
    config["KeyEventHandling"]["ipc_port"] = str(port)
    print("Set port %d"%port)
    

def source_setup():
    from .. import Amp
    input("On your amp, select the input source that you want to control with this program and press ENTER.")
    source = Amp(protocol=".denon", cls="BasicAmp").source
    print("Registered input source `%s`."%source)
    config["Amp"]["source"] = source
    

def setup_xorg_key_binding():
    xbindkeysrc = os.path.expanduser("~/.xbindkeysrc")
    if not os.path.exists(xbindkeysrc):
        os.system("xbindkeys -d > %s"%xbindkeysrc)
    content = pkgutil.get_data(__name__,"../share/xbindkeysrc").decode()
    with open(xbindkeysrc,"a+") as fp:
        fp.write("\n%s"%content)
    os.system("xbindkeys --poll-rc")
    print("Written to %s."%xbindkeysrc)
    

class DenonDiscoverer(object):
    """
    Search local network for Denon amp
    """

    def __init__(self):
        for host in PrivateNetwork().find_hosts():
            if host.lower().startswith("denon"):
                print("Found '%s'."%host)
                self.denon = host
                config["Amp"]["Host"] = host
                return
        raise Exception("No Denon amp found in local network. Check if amp is connected or"
            " set IP manually.")
        

class PrivateNetwork(object):

    def find_hosts(self):
        for e in self.by_arp(): yield e
        for e in self.by_nmap(): yield e
        
    def by_arp(self):
        try:
            devices = subprocess.run(
                ["/usr/sbin/arp","-a"],stdout=subprocess.PIPE).stdout.decode().strip().split("\n")
        except Exception as e:
            sys.stderr.write("ERROR detecting Denon IP address.\n")
            return []
        devices = [e.split(" ",1)[0] for e in devices]
        return devices

    def _get_private_networks(self):
        for iface in netifaces.interfaces():
            for l in netifaces.ifaddresses(iface).values():
                for d in l:
                    try: ip = ipaddress.ip_network(
                        "%s/%s"%(d.get("addr"),d.get("netmask")),strict=False)
                    except Exception as e: continue
                    if not ip.is_private: continue
                    yield(str(ip))
    
    def by_nmap(self):
        nm = nmap.PortScanner()
        for network in self._get_private_networks():
            if network.startswith("127."): continue
            print("Scanning %s ..."%network)
            nm.scan(network,"23",arguments="")
            hosts = [hostnames["name"] 
                for ip,d in nm.analyse_nmap_xml_scan()["scan"].items() 
                for hostnames in d["hostnames"]
            ]
            for h in hosts: yield h


def main(): Main()()
if __name__ == "__main__":
    main()

