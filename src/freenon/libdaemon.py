import threading, time, signal, sys, socket
import dbus
from datetime import timedelta, datetime
from gi.repository import GLib, Gio
from .denon import Denon, roundVolume
#from .config import config


class PluginInterface(object):
    
    def getVolume(self): pass #return 50
    def getMuted(self): pass #return False
    def update_volume(self, volume): pass
    def update_muted(self, muted): pass
        
        
class IfConnected(object):
    """ with IfConnected(EventHandler x):
        stops execution on connection errors and fire events
    """

    def __init__(self, event_listener):
        self.el = event_listener
        
    def __enter__(self): pass

    def __exit__(self, type, value, traceback):
        if type not in (socket.timeout, socket.gaierror, socket.herror): return False
        self.el.on_connection_lost()
        sys.stderr.write("[Warning] dropping call\n")
        self.el.denon.wait_for_connection()
        self.el.on_connect()
        return True


updateLock = threading.Lock()
avrLock = threading.Lock()
def threadlock(lock):
    def decorator(func):
        def f(*args,**xargs):
            lock.acquire()
            try: return func(*args,**xargs)
            finally: lock.release()
        return f
    return decorator
    
    
class EventHandler(object):
    """
    Event handler that keeps up to date the plugin data such as the volume
    and controls the AVR's power state.
    """
    
    def __init__(self, plugin, verbose=False):
        self.plugin = plugin
        self.denon = Denon(verbose=verbose)
        self.denon.ifConnected = IfConnected(self)
        self.on_startup()
        signal.signal(signal.SIGTERM, self.on_shutdown)
        threading.Thread(target=DBusListener(self)).start()
        self.avrListener = AvrListener(self, self.denon)
        threading.Thread(target=self.avrListener).start()

    @threadlock(avrLock)
    @threadlock(updateLock)
    def updateAvrValues(self):
        pluginmuted = self.plugin.getMuted()
        pluginvol = roundVolume(self.plugin.getVolume())
        with self.denon.ifConnected: 
            if self.denon.muted != pluginmuted: self.denon.muted = pluginmuted
            if not pluginmuted and self.denon.volume != pluginvol: self.denon.volume = pluginvol
            if hasattr(self,"avrListener"): self.avrListener.reset()
    
    @threadlock(updateLock)
    def updatePluginValues(self, denonReset=True):
        """ Set plugin volume and mute according to AVR """
        if denonReset: self.denon.reset()
        with self.denon.ifConnected: 
            avr_muted = self.denon.muted
            self.plugin.update_muted(avr_muted)
            if not avr_muted: self.plugin.update_volume(self.denon.volume)

    def denon_connect_sync_wait(self):
        self.denon.wait_for_connection()
        self.on_connect()
        #if not self.denon.running():
        #self.denon.poweron()
        self.updateAvrValues()

    def on_startup(self):
        """ program start """
        print("[Event] Startup", file=sys.stderr)
        self.denon_connect_sync_wait()
        
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
        self.denon_connect_sync_wait()
        
    def on_connect(self):
        """ Execute when connected e.g. after connection aborted """
        print("[Event] connected to %s"%self.denon.host, file=sys.stderr)
        if self.denon.running(): self.updatePluginValues()
        
    def on_connection_lost(self):
        print("[Event] connection lost", file=sys.stderr)
    
    def on_plugin_change(self):
        print("[Event] Plugin change", file=sys.stderr)
        self.updateAvrValues()
        
    def on_avr_change(self, attr):
        print("[Event] AVR attribute changed", file=sys.stderr)
        self.updatePluginValues(False)
        
    def on_avr_poweron(self):
        print("[Event] AVR power on", file=sys.stderr)
        time.sleep(3) #TODO
        self.updateAvrValues()
        
    def on_avr_poweroff(self):
        print("[Event] AVR power off", file=sys.stderr)
        

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


class AvrListener(object):
    observe=["volume","muted","is_running"]
        
    def __init__(self, eh, denon):
        self.eh = eh
        self.denon = denon

    def reset(self):
        self.lastUpdate = datetime.now()

    def __call__(self):
        self.reset()
        while True:
            time.sleep(1)
            with self.denon.ifConnected:
                #if not avrLock.locked(): 
                self._checkAttributes()

    def _checkAttributes(self):
        avrLock.acquire()
        try:
            if datetime.now() < self.lastUpdate+timedelta(seconds=1): return
            #print("[AvrListener] check", file=sys.stderr)
            previous = {attr:getattr(self.denon,attr) for attr in self.observe}
            self.denon.reset()
            new = {attr:getattr(self.denon,attr) for attr in self.observe}
        finally: avrLock.release()
        for attr in self.observe:
            if new[attr] != previous[attr]:
                if attr == "is_running":
                    if new[attr]: self.eh.on_avr_poweron()
                    else: self.eh.on_avr_poweroff()
                elif self.denon.is_running: 
                    self.eh.on_avr_change(attr)
    
