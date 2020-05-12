import threading, time, signal, sys
from datetime import timedelta, datetime
from gi.repository import GLib, Gio
from .denon import Denon
#from .config import config


        
class EventHandler(Denon):
    """
    Event handler that keeps up to date the plugin data such as the volume
    and controls the AVR's power state.
    """
    
    def __init__(self, verbose=False):
        self.denon = self # TODO
        super(EventHandler,self).__init__(verbose=verbose)
        threading.Thread(target=self.on_startup, name="on_startup", daemon=True).start()
        signal.signal(signal.SIGTERM, self.on_shutdown)
        threading.Thread(target=DBusListener(self), name="DBusListener", daemon=True).start()

    def loop(self):
        try:
            while True: time.sleep(1000)
        except KeyboardInterrupt: pass
    
    @property
    def update_actions(self):
        return {
            "is_running": 
                lambda value:{True:self.on_avr_poweron, False:self.on_avr_poweroff}[value](),
        }

    def on_startup(self):
        """ program start """
        print("[Event] Startup", file=sys.stderr)
        if not self.denon.connected: self.denon.connect(-1)
        
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
            #self.denon.poll_all() # TODO: better asynchronous and return
            self.denon.features["is_running"]._poll()
            for attr, f in self.denon.features.items():
                    if not f._isset() or self.denon.is_running: 
                        old, new = f._poll()
                        if old != new: self.on_avr_change(attr,new)
        except ConnectionError: pass
            
    def on_connection_lost(self):
        print("[Event] connection lost", file=sys.stderr)
        super(EventHandler,self).on_connection_lost()
        
    def on_avr_poweron(self):
        print("[Event] AVR power on", file=sys.stderr)
        time.sleep(3) #TODO
        # TODO: maybe do not set vol if muted? care about which attibutes are being sent?
        for attr, f in self.denon.features.items():
            f._send()
        
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


