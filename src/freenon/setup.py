#!/usr/bin/env python3
# -*- coding: utf-8 -*- 

import subprocess, sys, netifaces, ipaddress, nmap
from .config import config


class DenonDiscoverer(object):
    """
    Search local network for Denon AVR
    """

    def __init__(self):
        for host in PrivateNetwork().find_hosts():
            if host.lower().startswith("denon"):
                print("Found '%s'."%host)
                self.denon = host
                config["DEFAULT"]["Host"] = host
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


def main(): DenonDiscoverer()
if __name__ == "__main__":
    main()

