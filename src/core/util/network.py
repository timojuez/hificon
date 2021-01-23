import sys, subprocess, ipaddress
try: import nmap
except ImportError: pass
try: import netifaces
except ImportError: pass


class PrivateNetwork(object):

    def find_hosts(self):
        """
        Discover hosts in current private network. This yields hostnames
        """
        for e in self.by_arp(): yield e
        for e in self.by_nmap(): yield e
        
    def by_arp(self):
        try:
            devices = subprocess.run(
                ["/usr/sbin/arp","-a"],stdout=subprocess.PIPE).stdout.decode().strip().split("\n")
        except Exception as e:
            sys.stderr.write("ERROR using arp.\n")
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

