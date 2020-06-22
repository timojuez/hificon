import sys, os, argparse, pkgutil, socket
from ..util.network import PrivateNetwork
from ..config import config, FILE
from .. import NAME, Amp


class Main(object):

    def __init__(self):
        parser = argparse.ArgumentParser(description='%s Setup Tool'%NAME)
        discover = parser.add_mutually_exclusive_group()
        discover.add_argument('--discover', dest="nothing", action="store_false", help='Include Denon amp discovery (default)')
        discover.add_argument('--no-discover', default=discover_denon, dest="discover", action="store_false")

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
    config["Service"]["ipc_port"] = str(port)
    print("Set port %d"%port)
    

def source_setup():
    if input("On your amp, select the input source that you want to control "
        "with this program and press ENTER. [s]kip? ") == "s": return
    with Amp(protocol=".denon") as amp:
        source = amp.source
    print("Registered input source `%s`."%source)
    config["Amp"]["source"] = source
    

def setup_xorg_key_binding():
    xbindkeysrc = os.path.expanduser("~/.xbindkeysrc")
    if not os.path.exists(xbindkeysrc):
        os.system("xbindkeys -d > %s"%xbindkeysrc)
    content = pkgutil.get_data(__name__,"../share/xbindkeysrc").decode()
    with open(xbindkeysrc,"a+") as fp:
        fp.write("\n%s"%content)
    print("Written to %s."%xbindkeysrc)
    print("Restarting xbindkeys...")
    os.system("killall xbindkeys")
    os.system("xbindkeys")
    

def discover_denon():
    """
    Search local network for Denon amp
    """
    for host in PrivateNetwork().find_hosts():
        if host.lower().startswith("denon"):
            with Amp(protocol=".denon", host=host) as amp:
                try: name = amp.denon_name
                except: name = host
            print("Found %s on %s."%(name, host))
            config["Amp"]["Host"] = host
            config["Amp"]["Name"] = name
            return
    raise Exception("No Denon amp found in local network. Check if amp is connected or"
        " set IP manually.")


def main(): Main()()
if __name__ == "__main__":
    main()

