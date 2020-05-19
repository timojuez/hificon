import time, signal, sys
from threading import Timer, Thread
from datetime import timedelta, datetime
from gi.repository import GLib, Gio
from .denon import Denon
from .config import config


def call_sequence(*functions):
    return lambda *args,**xargs: [f(*args,**xargs) for f in functions]


class CommonEventHandler(object):
    def __init__(self):
        Thread(target=self.on_startup, name="on_startup", daemon=True).start()
        signal.signal(signal.SIGTERM, self.on_shutdown)
        Thread(target=DBusListener(self), name="DBusListener", daemon=True).start()
        
    def on_startup(self): pass
    def on_shutdown(self): pass
    def on_suspend(self): pass
    def on_resume(self): pass


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


class AbstractPulse(object):
    def __init__(self): self.pulse = pulsectl.Pulse("Freenon")
    
    def pulse_is_playing(self):
        return len(self.pulse.sink_input_list()) > 0
    
    
class PulseEventHandler(CommonEventHandler,AbstractPulse):

    def __init__(self, *args, **xargs):
        AbstractPulse.__init__(self)
        CommonEventHandler.__init__(self, *args, **xargs)
        PulseListener(self)()
        
    def on_connect(self):
        super(PulseEventHandler,self).on_connect()
        if self.pulse_is_playing():
            try: self.denon.poweron()
            except ConnectionError: pass


class PulseListener(AbstractPulse):
    """ Listen for pulseaudio change events """
    
    def __init__(self, el):
        super(PulseListener,self).__init__()
        self.el = el

    def __call__(self, *args, **xargs):
        Thread(target=self.loop, name=self.__class__.__name__, daemon=True,
            args=args, kwargs=xargs).start()
        
    def loop(self):
        #self.pulse.event_mask_set('all')
        self.pulse.event_mask_set(pulsectl.PulseEventMaskEnum.sink,
            pulsectl.PulseEventMaskEnum.sink_input)
        self.pulse.event_callback_set(self.callback)
        while True:
            try: self.pulse.event_listen()
            except KeyboardInterrupt: return
            if self.ev.facility == pulsectl.PulseEventFacilityEnum.sink:
                self._on_pulse_sink_event()
            elif self.ev.facility == pulsectl.PulseEventFacilityEnum.sink_input:
                self._on_pulse_sink_input_event()

    def callback(self, ev):
        self.ev = ev
        #print('Pulse event:', ev)
        raise pulsectl.PulseLoopStop

    def _on_pulse_sink_event(self):
        if self.ev.t == pulsectl.PulseEventTypeEnum.change:
            pass

    def _on_pulse_sink_input_event(self):
        if self.ev.t == pulsectl.PulseEventTypeEnum.new:
            print("[Pulse] start playing")
            if hasattr(self,"poweroff"): self.poweroff.cancel()
            try: self.el.denon.poweron()
            except ConnectionError: pass
        elif pulsectl.PulseEventTypeEnum.remove and not self.pulse_is_playing():
            print("[Pulse] stopped")
            self.start_poweroff_timeout()
    
    def start_poweroff_timeout(self):
        try: timeout = config.getfloat("Pulse","poweroff_timeout")*60
        except ValueError: return
        if not timeout: return
        self.poweroff = Timer(timeout,self.on_idle)
        self.poweroff.start()
    
    def on_idle(self):
        print("[Pulse] idling")
        try: self.el.denon.poweroff()
        except ConnectionError: pass


try: import pulsectl
except ImportError: _EventHandler = CommonEventHandler
else: _EventHandler = PulseEventHandler


class DenonWithEvents(Denon,_EventHandler):
    """
    Event handler that keeps up to date the plugin data such as the volume
    and controls the AVR's power state.
    """
    
    def __init__(self, verbose=False, **callbacks):
        self.denon = self
        for name, callback in callbacks.items():
            setattr(self, name, call_sequence(getattr(self,name), callback))
        Denon.__init__(self,verbose=verbose)
        _EventHandler.__init__(self)

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

    def on_shutdown(self, sig, frame):
        """ when shutting down computer """
        try: self.denon.poweroff()
        except ConnectionError: pass
        
    def on_suspend(self):
        try: self.denon.poweroff()
        except ConnectionError: pass
    
    def on_resume(self):
        """ Is being executed after resume from suspension """
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
        super(EventHandler,self).on_connection_lost()
        
    def on_avr_poweron(self):
        pass
        
    def on_avr_poweroff(self):
        pass

    def on_avr_change(self, attrib, value):
        super(EventHandler,self).on_avr_change(attrib, value)
        func = self.update_actions.get(attrib)
        if func: func(value)

def echo_call(name, func):
    def call(self,*args,**xargs):
        print("[%s] %s"%(self.__class__.__name__,name), file=sys.stderr) 
        return func(self,*args,**xargs)
    return call
for k in dir(DenonWithEvents):
    if k.startswith("on_"): setattr(DenonWithEvents,k,echo_call(k,getattr(DenonWithEvents,k)))


EventHandler = DenonWithEvents

