import time, signal, sys
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
        self.pl = Pulse(self)
        
    def on_connect(self):
        # AVR connected
        super(PulseSystemEvents,self).on_connect()
        if self.pl.connected and self.pl.pulse_is_playing: self.on_start_playing()

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


# move to pulse.py
import pulsectl


class ConnectedPulse(pulsectl.Pulse):

    def __init__(self,*args,**xargs):
        super().__init__(*args,connect=False,**xargs)
        self.connect_pulse()

    def connect_pulse(self):
        def connect():
            self.connect()
            self.on_connected()
        def keep_reconnecting():
            print("[%s] disconnected."%self.__class__.__name__, file=sys.stderr)
            while True:
                try: connect()
                except pulsectl.pulsectl.PulseError: time.sleep(3)
                else: break
        try: connect()
        except pulsectl.pulsectl.PulseError:
            Thread(target=keep_reconnecting,daemon=True).start()
    
    def on_connected(self):
        print("[%s] Connected to Pulseaudio."%self.__class__.__name__, file=sys.stderr)
    
    def is_playing(self):
        return len(self.sink_input_list()) > 0
    
    
class Pulse(ConnectedPulse):
    """ Listen for pulseaudio change events """
    
    def __init__(self, el):
        self.pulse_is_playing = False
        self.el = el
        self.pulse = self
        super().__init__("Freenon")

    def on_connected(self):
        # Pulseaudio connected
        super().on_connected()
        try: self.pulse_is_playing = self.pulse.is_playing()
        except pulsectl.pulsectl.PulseDisconnected: return self.connect_pulse() 
        Thread(target=self.loop, name=self.__class__.__name__, daemon=True).start()
        
    def loop(self):
        try:
            #self.pulse.event_mask_set('all')
            self.pulse.event_mask_set(pulsectl.PulseEventMaskEnum.sink,
                pulsectl.PulseEventMaskEnum.sink_input)
            self.pulse.event_callback_set(self._callback)
            while True:
                self.pulse.event_listen()
                if self.ev.facility == pulsectl.PulseEventFacilityEnum.sink:
                    self._on_pulse_sink_event()
                elif self.ev.facility == pulsectl.PulseEventFacilityEnum.sink_input:
                    self._on_pulse_sink_input_event()
        except KeyboardInterrupt: pass
        except pulsectl.pulsectl.PulseDisconnected: self.connect_pulse()
        
    def _callback(self, ev):
        self.ev = ev
        #print('Pulse event:', ev)
        raise pulsectl.PulseLoopStop

    def _on_pulse_sink_event(self):
        if self.ev.t == pulsectl.PulseEventTypeEnum.change:
            pass

    def _on_pulse_sink_input_event(self):
        self.pulse_is_playing = self.pulse.is_playing()
        if self.ev.t == pulsectl.PulseEventTypeEnum.new:
            self.el.on_start_playing()
        elif self.ev.t == pulsectl.PulseEventTypeEnum.remove and not self.pulse_is_playing:
            self.el.on_stop_playing()


try: import pulsectl
except ImportError: SystemEvents = CommonSystemEvents
else: SystemEvents = PulseSystemEvents


