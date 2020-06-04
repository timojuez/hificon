import signal
from threading import Thread


class SignalMixin(object):

    def __init__(self,*args,**xargs):
        super().__init__(*args,**xargs)
        Thread(target=self.on_startup, name="on_startup", daemon=True).start()
        signal.signal(signal.SIGTERM, self.on_shutdown)
        
    def on_startup(self): pass
    def on_shutdown(self): pass


class PulseMixin(object):

    def __init__(self, *args, **xargs):
        super().__init__(*args, **xargs)
        self.pulse = PulseListener(self, connect=False, consider_old_sinks=False)
        self.pulse.connect_async()
        
    def on_connect(self):
        # Amp connected
        super().on_connect()
        if self.pulse.connected and self.pulse.is_playing: self.on_start_playing()

    def on_pulse_connected(self): pass
    def on_start_playing(self): pass
    def on_stop_playing(self): pass


class DBusMixin(object):
    """
    Connects to system bus and fire events, e.g. on shutdown and suspend
    """
    
    def __init__(self, *args, **xargs):
        super().__init__(*args,**xargs)
        Thread(target=self._dbusListener, name="DBusListener", daemon=True).start()

    def _dbusListener(self):
        system_bus = Gio.bus_get_sync(Gio.BusType.SYSTEM, None)
        system_bus.signal_subscribe('org.freedesktop.login1',
            'org.freedesktop.login1.Manager',
            'PrepareForSleep',
            '/org/freedesktop/login1',
            None,
            Gio.DBusSignalFlags.NONE,
            self._onLoginmanagerEvent,
            None)
        loop = GLib.MainLoop()
        loop.run()
        
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

