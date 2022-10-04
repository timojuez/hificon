"""
Class that listens for system events such as shutdown, suspend, resume, sound playing.
The available events depend on the platform.
Example:
    class MyListener(SystemEvents):
        def on_shutdown(self): print("shutting down now!")
    with MyListener(): ...
"""

import signal, time, sys
from threading import Thread
from contextlib import AbstractContextManager


class _Abstract(AbstractContextManager):

    def __init__(self, *args, verbose=0, **xargs):
        super().__init__(*args, **xargs)


class SignalMixin(_Abstract):

    def __enter__(self):
        self._sigterm_handler = signal.getsignal(signal.SIGTERM)
        signal.signal(signal.SIGTERM, self.on_shutdown)
        Thread(target=self.on_startup, name="on_startup", daemon=True).start()
        return super().__enter__()

    def __exit__(self, *args, **xargs):
        super().__exit__(*args, **xargs)
        signal.signal(signal.SIGTERM, self._sigterm_handler)

    def on_startup(self): pass
    def on_shutdown(self, sig, frame): self.main_quit()
    def main_quit(self): sys.exit(0)


class PulseMixin(_Abstract):

    def __init__(self, *args, **xargs):
        super().__init__(*args, **xargs)
        self.pulse = PulseListener(self, consider_old_sinks=False, verbose=xargs.get("verbose",0) > 1)

    def __enter__(self):
        self.pulse.__enter__()
        return super().__enter__()

    def __exit__(self, *args, **xargs):
        super().__exit__(*args, **xargs)
        self.pulse.__exit__(*args, **xargs)

    def on_pulse_connected(self): pass
    def on_start_playing(self): pass
    def on_stop_playing(self): pass


class DBusMixin(_Abstract):
    """
    Connects to system bus and fire events, e.g. on shutdown and suspend
    """

    def __enter__(self):
        self.glib_mainloop = GLib.MainLoop()
        # _system_bus may not be deleted by garbage collector so adding it to self
        self._system_bus = Gio.bus_get_sync(Gio.BusType.SYSTEM, None)
        self._system_bus.signal_subscribe('org.freedesktop.login1',
            'org.freedesktop.login1.Manager',
            'PrepareForSleep',
            '/org/freedesktop/login1',
            None,
            Gio.DBusSignalFlags.NONE,
            self._onLoginmanagerEvent,
            None)
        Thread(target=self.glib_mainloop.run, name="GLib.MainLoop", daemon=True).start()
        return super().__enter__()

    def __exit__(self, *args, **xargs):
        super().__exit__(*args, **xargs)
        del self._system_bus # unsubscribe
        self.glib_mainloop.quit()

    def _onLoginmanagerEvent(self, conn, sender, obj, interface, signal, parameters, data):
        if parameters[0]:
            self.on_suspend() 
        else: 
            self.on_resume()

    def on_suspend(self): pass
    def on_resume(self): pass


inheritance = (SignalMixin,)

try: from .pulse import PulseListener
except ImportError: pass
else: inheritance += (PulseMixin,)

try: from gi.repository import GLib, Gio
except ImportError: pass
else: inheritance += (DBusMixin,)

class SystemEvents(*inheritance): pass

