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
        
        
class EventHandler(Denon):
    """
    Event handler that keeps up to date the plugin data such as the volume
    and controls the AVR's power state.
    """
    
    def __init__(self, plugin, verbose=False):
        self.plugin = plugin
        super(EventHandler,self).__init__(verbose=verbose)
        self.denon = self
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
            
    def updateAvrValues(self):
        pluginmuted = self.plugin.getMuted()
        try:
            self.denon.muted = pluginmuted
            if not pluginmuted: self.denon.volume = self.plugin.getVolume()
        except ConnectionError: pass

    def on_startup(self):
        """ program start """
        print("[Event] Startup", file=sys.stderr)
        self.denon_connect()
        
    def on_shutdown(self, sig, frame):
        """ when shutting down computer """
        print("[Event] Shutdown", file=sys.stderr)
        try: self.denon.poweroff()
        except ConnectionError: pass
        
    def on_suspend(self):
        print("[Event] Suspend", file=sys.stderr)
        try: self.denon.poweroff()
        except ConnectionError: pass
    
    def on_resume(self):
        """ Is being executed after resume from suspension """
        print("[Event] Resume", file=sys.stderr)
        self.on_connection_lost()
        
    def on_connect(self):
        """ Execute when connected e.g. after connection aborted """
        super(EventHandler,self).on_connect()
        try: 
            self.denon.poll_all() # better asynchronous and return
            if self.denon.is_running:
                for attr, func in self.update_actions.items():
                    value = getattr(self.denon, attr)
                    func(value)
        except ConnectionError: pass
            
    def on_connection_lost(self):
        print("[Event] connection lost", file=sys.stderr)
        super(EventHandler,self).on_connection_lost()
    
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
        super(EventHandler,self).on_avr_change(attrib, value)
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


