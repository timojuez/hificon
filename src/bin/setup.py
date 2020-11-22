import sys, os, argparse, pkgutil, socket
from contextlib import suppress
from urllib.parse import urlparse
from ..util import ssdp
from ..config import config, FILE
from .. import NAME, PKG_NAME, Amp, protocol


def autostart():
    if input("Add %s to autostart for current user? [Y/n] "%NAME) == "n": return
    return autostart_win() if sys.platform.startswith("win") else autostart_gnu()


def autostart_win():
    import getpass
    bat_path = r'C:\Users\%s\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup'%getpass.getuser()
    with open("%s\\%s.bat"%(bat_path, PKG_NAME), "w") as fp:
        fp.write(r'start "" %s' % os.path.realpath(__file__)) # TODO: file path


def autostart_gnu():
    desktop = pkgutil.get_data(__name__,"../share/hificon.desktop").decode()
    with open(os.path.expanduser("~/.config/autostart/%s.desktop"%PKG_NAME), "w") as fp:
        fp.write(desktop)


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
    if sys.platform != "linux": return
    if input("Bind mouse keys to volume and modify ~/.xbindkeysrc? [Y/n] ") == "n": return
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


arguments = [
    # arg,      func,           help,               default
    ("discover", discover_denon, "Include Denon amp discovery", True),
    ("autostart", autostart, "Add tray icon to autostart", True),
    ("keys", setup_xorg_key_binding, "Setup Xorg mouse and keyboard volume keys binding for current user", True),
    ("source-options-setup", source_options_setup, "Refresh input source list", True),
    ("source-setup", source_setup, "Connect Denon amp source setting to computer", True),
    ("set-port", set_port, "Set a port for inter process communication", True),
]


class Main(object):

    def __init__(self):
        self.parser = argparse.ArgumentParser(description='%s Setup Tool'%NAME)
        for args in arguments: self.add_bool_arg(*args)
        self.parser.add_argument("-v",'--verbose', default=False, action='store_true', help='Verbose mode')
        self.args = self.parser.parse_args()
        
    def add_bool_arg(self, arg, func, help, default=True):
        group = self.parser.add_mutually_exclusive_group()
        group.add_argument("--%s"%arg, default=default, action="store_true",
            help = "%s (default)"%help if default else help)
        group.add_argument("--no-%s"%arg, dest=arg, action="store_false",
            help="" if default else "(default)")
    
    def __call__(self):
        Setup.setup(steps=[a[0] for a in arguments if getattr(self.args, a[0])])


class Setup:
    _dir = os.path.expanduser("~/.%s"%PKG_NAME)

    @classmethod
    def configured(self): return os.path.exists(self._dir)
    
    @classmethod
    def setup(self, steps=None):
        if steps:
            assert(isinstance(steps,list))
            invalid = set(steps).difference([a[0] for a in arguments])
            if invalid: raise ValueError("Invalid steps: %s"%invalid)
        if os.path.exists(FILE) and input("This will modify `%s`. Proceed? [y/N] "%FILE) != "y": return
        with suppress(OSError): os.mkdir(self._dir)
        for arg, func, help, default in arguments:
            if steps and arg not in steps: continue
            try: func()
            except Exception as e:
                print("Exception in %s: %s"%(arg,repr(e)))
            print()
        print("done. The service needs to be (re)started.")

    


def main(): Main()()
if __name__ == "__main__":
    main()

