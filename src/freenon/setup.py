#!/usr/bin/env python3
# -*- coding: utf-8 -*- 

import subprocess, sys, netifaces, ipaddress, nmap, os, argparse, pkgutil
from .config import config


class Main(object):

    def __init__(self):
        parser = argparse.ArgumentParser(description='Freenon Setup Tool')
        discover = parser.add_mutually_exclusive_group()
        discover.add_argument('--discover', default=True, action="store_true", help='Include Denon AVR discovering (default)')
        discover.add_argument('--no-discover', dest="discover", action="store_false")

        keys = parser.add_mutually_exclusive_group()
        keys.add_argument('--keys', default=False, action="store_true", help='Setup Xorg mouse and keyboard volume keys binding for current user')
        keys.add_argument('--no-keys', dest="keys", action="store_false", help='(default)')

        source_setup = parser.add_mutually_exclusive_group()
        source_setup.add_argument('--source-setup', default=True, action="store_true", help='Connect Denon AVR source setting to computer (default)')
        source_setup.add_argument('--no-source-setup', dest="discover", action="store_false")
        
        parser.add_argument("-v",'--verbose', default=False, action='store_true', help='Verbose mode')
        self.args = parser.parse_args()
        
    def __call__(self):
        if self.args.discover: DenonDiscoverer()
        if self.args.source_setup: source_setup()
        if self.args.keys: setup_xorg_key_binding()
        

def source_setup():
    from .denon import BasicAmp
    input("On your AVR, select the input source that you want to control with this program and press ENTER.")
    amp = BasicAmp()
    amp.connect()
    config["AVR"]["source"] = amp.source
    config.save()
    

def setup_xorg_key_binding():
    if not os.path.exists(os.path.expanduser("~/.xbindkeysrc")):
        os.system("xbindkeys -d > ~/.xbindkeysrc")
    content = pkgutil.get_data(__name__,"share/xbindkeysrc").decode()
    with open(os.path.expanduser("~/.xbindkeysrc"),"a+") as fp:
        fp.write("\n%s"%content)
    os.system("xbindkeys --poll-rc")
    

class DenonDiscoverer(object):
    """
    Search local network for Denon AVR
    """

    def __init__(self):
        for host in PrivateNetwork().find_hosts():
            if host.lower().startswith("denon"):
                print("Found '%s'."%host)
                self.denon = host
                config["AVR"]["Host"] = host
                config.save()
                return
        raise Exception("No Denon AVR found in local network. Check if AVR is connected or"
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

