"""
Class that listens for system events such as shutdown, suspend, resume, sound playing.
The available events depend on the platform.
Example:
    class MyListener(SystemEvents):
        def on_shutdown(self): print("shutting down now!")
    MyListener().mainloop()
"""

import signal, time, sys
from threading import Thread


class _Abstract(object):

    def __init__(self, *args, verbose=0, **xargs):
        super().__init__(*args,**xargs)
        
    def mainloop(self, *args, **xargs):
        if hasattr(super(), "mainloop"): return super().mainloop(*args, **xargs)
        else:
            try:
                while True: time.sleep(1000)
            except KeyboardInterrupt: pass


class SignalMixin(_Abstract):

    def __init__(self,*args,**xargs):
        super().__init__(*args,**xargs)
        Thread(target=self.on_startup, name="on_startup", daemon=True).start()
        signal.signal(signal.SIGTERM, self.on_shutdown)
        
    def on_startup(self): pass
    def on_shutdown(self, sig, frame): self.main_quit()
    def main_quit(self): sys.exit(0)


class PulseMixin(_Abstract):

    def __init__(self, *args, **xargs):
        super().__init__(*args, **xargs)
        self.pulse = PulseListener(self, connect=False, consider_old_sinks=False, verbose=xargs.get("verbose",0) > 1)
        self.pulse.connect_async()
        
    def on_pulse_connected(self): pass
    def on_start_playing(self): pass
    def on_stop_playing(self): pass


class DBusMixin(_Abstract):
    """
    Connects to system bus and fire events, e.g. on shutdown and suspend
    """

    def mainloop(self,*args,**xargs):
        system_bus = Gio.bus_get_sync(Gio.BusType.SYSTEM, None)
        system_bus.signal_subscribe('org.freedesktop.login1',
            'org.freedesktop.login1.Manager',
            'PrepareForSleep',
            '/org/freedesktop/login1',
            None,
            Gio.DBusSignalFlags.NONE,
            self._onLoginmanagerEvent,
            None)
        Thread(target=GLib.MainLoop().run, name="GLib.MainLoop", daemon=True).start()
        super().mainloop(*args,**xargs)
        
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

