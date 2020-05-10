import threading, time, signal, sys
from datetime import timedelta, datetime
from gi.repository import GLib, Gio
from .denon import Denon
#from .config import config


class PluginInterface(object):
    
    def getVolume(self): pass #return 50
    def getMuted(self): pass #return False
    def update_volume(self, volume): pass
    def update_muted(self, muted): pass
    def update_maxvol(self, maxvol): pass
        
        
class IfConnected(object):
    """ with IfConnected(EventHandler x):
        stops execution on connection errors and fire events
    """

    def __init__(self, event_listener):
        self.el = event_listener
        
    def __enter__(self): pass

    def __exit__(self, type, value, traceback):
        if type not in (EOFError,): return False
        self.el.on_connection_lost()
        sys.stderr.write("[Warning] dropping call\n")
        self.el.denon.wait_for_connection()
        self.el.on_connect()
        return True

"""
updateLock = threading.Lock()
def threadlock(lock):
    def decorator(func):
        def f(*args,**xargs):
            lock.acquire()
            try: return func(*args,**xargs)
            finally: lock.release()
        return f
    return decorator
"""

    
class EventHandler(object):
    """
    Event handler that keeps up to date the plugin data such as the volume
    and controls the AVR's power state.
    """
    
    def __init__(self, plugin, verbose=False):
        self.plugin = plugin
        self.denon = Denon(verbose=verbose) # TODO: may raise on connect()
        self.denon.register_callback(self.on_avr_change)
        self.denon.ifConnected = IfConnected(self)
        threading.Thread(target=self.on_startup, name="on_startup", daemon=True).start()
        signal.signal(signal.SIGTERM, self.on_shutdown)
        threading.Thread(target=DBusListener(self), name="DBusListener", daemon=True).start()
        AvrListener(self, self.denon)()

    def loop(self):
        try:
            while True: time.sleep(1000)
        except KeyboardInterrupt: pass
    
    @property
    def update_actions(self):
        return {
            "is_running": 
                lambda value:{True:self.on_avr_poweron, False:self.on_avr_poweroff}[value](),
            "muted": self.plugin.update_muted,
            "volume": self.plugin.update_volume,
            "maxvol": self.plugin.update_maxvol,
        }
            
    #@threadlock(updateLock)
    def updateAvrValues(self):
        pluginmuted = self.plugin.getMuted()
        with self.denon.ifConnected:
            self.denon.muted = pluginmuted
            if not pluginmuted: self.denon.volume = self.plugin.getVolume()
    
    #@threadlock(updateLock)
    def updatePluginValues(self):
        for attr, func in self.update_actions.items():
            value = getattr(self.denon, attr)
            func(value)

    def denon_connect(self):
        self.denon.wait_for_connection()
        self.on_connect()

    def on_startup(self):
        """ program start """
        print("[Event] Startup", file=sys.stderr)
        self.denon_connect()
        
    def on_shutdown(self, sig, frame):
        """ when shutting down computer """
        print("[Event] Shutdown", file=sys.stderr)
        with self.denon.ifConnected: self.denon.poweroff()
        
    def on_suspend(self):
        print("[Event] Suspend", file=sys.stderr)
        with self.denon.ifConnected: self.denon.poweroff()
    
    def on_resume(self):
        """ Is being executed after resume from suspension """
        print("[Event] Resume", file=sys.stderr)
        self.on_connection_lost()
        self.denon_connect()
        
    def on_connect(self):
        """ Execute when connected e.g. after connection aborted """
        print("[Event] connected to %s"%self.denon.host, file=sys.stderr)
        self.denon.poll_all()
        if self.denon.is_running: self.updatePluginValues()
        
    def on_connection_lost(self):
        print("[Event] connection lost", file=sys.stderr)
    
    def on_plugin_change(self):
        print("[Event] Plugin change", file=sys.stderr)
        self.updateAvrValues()
        
    def on_avr_poweron(self):
        print("[Event] AVR power on", file=sys.stderr)
        time.sleep(3) #TODO
        self.updateAvrValues()
        
    def on_avr_poweroff(self):
        print("[Event] AVR power off", file=sys.stderr)

    def on_avr_change(self, attrib, value):
        print("[Event] AVR change", file=sys.stderr)
        func = self.update_actions.get(attrib)
        if func: func(value)
        

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


