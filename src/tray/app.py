import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk
import argparse
from threading import Thread
from contextlib import ExitStack
from .common import gtk, config, APP_NAME
from .setup_wizard import SetupWizard
from .power_control import PowerControlMixin
from .notifications import NotificationMixin
from .key_binding import KeyBinding
from .tray import TrayMixin


class App(NotificationMixin, TrayMixin, KeyBinding, PowerControlMixin): pass


class AppManager:

    def __init__(self, verbose):
        self.main_app = None
        self._exit_stack = ExitStack()
        self.verbose = verbose+1

    def mainloop(self):
        with self._exit_stack: Gtk.main()

    @gtk
    def run_app(self, uri=None, setup=False):
        self._exit_stack.close()
        if setup or not config["target"]["setup_mode"]:
            return SetupWizard(self, first_run=True).show()
        self.main_app = self._exit_stack.enter_context(App(self, uri, verbose=self.verbose))

    @gtk
    def main_quit(self):
        Gtk.main_quit()


def main():
    parser = argparse.ArgumentParser(description=APP_NAME)
    parser.add_argument('--setup', default=False, action="store_true", help='Run initial setup')
    parser.add_argument('-t', '--target', metavar="URI", type=str, default=None, help='Target URI')
    parser.add_argument('--verbose', '-v', action='count', default=0, help='Verbose mode')
    args = parser.parse_args()

    am = AppManager(verbose=args.verbose)
    Thread(target=lambda: am.run_app(args.target, args.setup), name="mainapp", daemon=True).start()
    am.mainloop()

