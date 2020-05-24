import signal
from threading import Thread
from gi.repository import GLib, Gio


class CommonSystemEvents(object):
    def __init__(self):
        Thread(target=self.on_startup, name="on_startup", daemon=True).start()
        signal.signal(signal.SIGTERM, self.on_shutdown)
        Thread(target=DBusListener(self), name="DBusListener", daemon=True).start()
        
    def on_startup(self): pass
    def on_shutdown(self): pass
    def on_suspend(self): pass
    def on_resume(self): pass


class PulseSystemEvents(CommonSystemEvents):

    def __init__(self, *args, **xargs):
        CommonSystemEvents.__init__(self, *args, **xargs)
        self.pulse = Pulse(self)
        
    def on_connect(self):
        # AVR connected
        super(PulseSystemEvents,self).on_connect()
        if self.pulse.connected and self.pulse.is_playing: self.on_start_playing()

    def on_start_playing(self): pass
    def on_stop_playing(self): pass


class DBusListener(object):
    """
    Connects to system bus and fire events, e.g. on shutdown and suspend
    """
    
    def __init__(self, event_listener):
        self.el = event_listener

    def __call__(self):
        system_bus = Gio.bus_get_sync(Gio.BusType.SYSTEM, None)
        system_bus.signal_subscribe('org.freedesktop.login1',
            'org.freedesktop.login1.Manager',
            'PrepareForSleep',
            '/org/freedesktop/login1',
            None,
            Gio.DBusSignalFlags.NONE,
            self.onLoginmanagerEvent,
            None)
        loop = GLib.MainLoop()
        loop.run()
        
    def onLoginmanagerEvent(self, conn, sender, obj, interface, signal, parameters, data):
        if parameters[0]:
            self.el.on_suspend() 
        else: 
            self.el.on_resume()


try: from .pulse import Pulse
except ImportError: SystemEvents = CommonSystemEvents
else: SystemEvents = PulseSystemEvents

