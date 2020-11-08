import sys, os, argparse, pkgutil, socket
from urllib.parse import urlparse
from ..util import ssdp
from ..config import config, FILE
from .. import NAME, Amp, protocol


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
        
        source_options = parser.add_mutually_exclusive_group()
        source_options.add_argument('--source-options-setup', dest="nothing", action="store_false", help='Refresh input source list (default)')
        source_options.add_argument('--no-source-options-setup', default=source_options_setup, dest="source_options_setup", action="store_false")
        
        port = parser.add_mutually_exclusive_group()
        port.add_argument('--set-port', dest="nothing", action="store_false", help='Set a port for inter process communication (default)')
        port.add_argument('--no-set-port', default=set_port, dest="set_port", action="store_false")
        
        parser.add_argument("-v",'--verbose', default=False, action='store_true', help='Verbose mode')
        self.args = parser.parse_args()
        
    def __call__(self):
        if os.path.exists(FILE) and input("This will modify `%s`. Proceed? [y/N] "%FILE) != "y": return
        for arg, func in filter(lambda e: callable(e[1]), self.args._get_kwargs()):
            try: func()
            except Exception as e:
                print("Exception in %s: %s"%(arg,repr(e)))
            print()
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
    with Amp() as amp:
        source = amp.source
    print("Registered input source `%s`."%source)
    config["Amp"]["source"] = source
    

def source_options_setup():
    with Amp() as amp:
        print("Registered the following input sources:")
        f = protocol.denon.SourceNames(amp)
        f.poll()
        for input_ in f.translation.values(): print("\t%s"%input_)
        config.setdict("Amp", "source_names", f.translation)


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
    def check_amp(host):
        try:
            with Amp(protocol=".denon", host=host) as amp:
                name = amp.denon_name
        except (ConnectionError, socket.timeout, socket.gaierror, socket.herror, OSError):
            return False
        print("Found %s on %s."%(name, host))
        config["Amp"]["Host"] = host
        config["Amp"]["Name"] = name
        config["Amp"]["protocol"] = ".denon"
        return True
    for response in ssdp.discover():
        if "denon" in response.st.lower() or "marantz" in response.st.lower():
            host = urlparse(response.location).hostname
            if check_amp(host): return
    #raise Exception("No Denon amp found. Check if amp is connected or"
    #    " set IP manually.")
    while True:
        host = input("No Denon amp found. Enter IP manually: ")
        if check_amp(host): return
        else: print("Cannot connect to host.")


def main(): Main()()
if __name__ == "__main__":
    main()

