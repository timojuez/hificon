import threading, time, signal, sys, socket
import dbus
from gi.repository import GLib, Gio
from .denon import Denon
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
        self.el.wait_for_connection()
        self.el.on_connect()
        return True

        
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

    def updateAvrValues(self):
        pluginmuted = self.plugin.getMuted()
        pluginvol = self.plugin.getVolume()
        with self.denon.ifConnected: 
            if self.denon.muted != pluginmuted: self.denon.muted = pluginmuted
            if not pluginmuted and self.denon.volume != pluginvol: self.denon.volume = pluginvol
    
    def updatePluginValues(self):
        """ Set plugin volume and mute according to AVR """
        self.denon.reset()
        with self.denon.ifConnected: 
            avr_muted = self.denon.muted
            self.plugin.update_muted(avr_muted)
            if not avr_muted: self.plugin.update_volume(self.denon.volume)

    def denon_connect_sync_wait(self):
        self.denon.wait_for_connection()
        self.on_connect()
        #if not self.denon.running():
        self.denon.poweron()
        self.updateAvrValues()

    def on_startup(self):
        """ program start """
        print("[Event] Startup")
        self.denon_connect_sync_wait()
        
    def on_shutdown(self, sig, frame):
        """ when shutting down computer """
        print("[Event] Shutdown")
        with self.denon.ifConnected: self.denon.poweroff()
        
    def on_suspend(self):
        print("[Event] Suspend")
        with self.denon.ifConnected: self.denon.poweroff()
    
    def on_resume(self):
        """ Is being executed after resume from suspension """
        print("[Event] Resume")
        self.denon_connect_sync_wait()
        
    def on_connect(self):
        """ Execute when connected e.g. after connection aborted """
        print("[Event] connected to %s"%self.denon.host)
        if self.denon.running(): self.updatePluginValues()
        
    def on_connection_lost(self):
        print("[Event] connection lost")
    
    def on_plugin_change(self):
        print("[Event] Plugin change")
        self.updateAvrValues()
        

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
    


