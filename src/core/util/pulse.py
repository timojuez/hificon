import pulsectl, sys
from threading import Thread, Event
from contextlib import AbstractContextManager


class ConnectedPulse(pulsectl.Pulse, AbstractContextManager):

    def __init__(self, *args, verbose=False, **xargs):
        super().__init__(*args, connect=False, **xargs)
        self._verbose = verbose
        self._disconnect_evt = Event()

    def __enter__(self):
        self._disconnect_evt.clear()
        self.connect_async()
        return super().__enter__()

    def __exit__(self, *args, **xargs):
        super().__exit__(*args, **xargs)
        self._disconnect_evt.set()

    def connect_async(self):
        def connect():
            self.connect()
            self.on_connected()
        def keep_reconnecting():
            while not self._disconnect_evt.is_set():
                try: connect()
                except pulsectl.pulsectl.PulseError: self._disconnect_evt.wait(3)
                else: break
        if self._disconnect_evt.is_set(): return
        if self._verbose: print("[%s] Connecting..."%self.__class__.__name__, file=sys.stderr)
        try: connect()
        except pulsectl.pulsectl.PulseError:
            Thread(name="%s_connecting"%self.__class__.__name__,target=keep_reconnecting,daemon=True).start()
    
    def on_connected(self):
        if self._verbose: print("[%s] Connected to Pulseaudio."%self.__class__.__name__, file=sys.stderr)
    
    
class PulseListener(ConnectedPulse):
    """ 
    Listen for pulseaudio change events
    call event_listener.on_start_playing and event_listener.on_stop_playing according to pulse.
    """
    
    def __init__(self, event_listener, consider_old_sinks=True, *args, **xargs):
        """
        @consider_old_sinks bool: If False, is_playing will consider only sinks that have
            been created after object initialisation
        """
        self._events = event_listener
        self._consider_old_sinks = consider_old_sinks
        self._sink_input_set = set()
        self.is_playing = set()
        super().__init__("PulseListener_for_%s"%self._events.__class__.__name__,*args,**xargs)

    def sink_input_set(self):
        comparable = lambda l: set(map(lambda e:frozenset(e.proplist.items()), l))
        try: return comparable(self.sink_input_list())
        except:
            if not self.connected: raise pulsectl.pulsectl.PulseDisconnected()
            raise
        
    def on_connected(self):
        # Pulseaudio connected
        super().on_connected()
        try: self._sink_input_set = self.sink_input_set()
        except pulsectl.pulsectl.PulseDisconnected: return self.connect_async()
        if self._consider_old_sinks: self.is_playing = self._sink_input_set
        self._events.on_pulse_connected()
        Thread(target=self.loop, name=self.__class__.__name__, daemon=True).start()
        
    def loop(self):
        try:
            #self.event_mask_set('all')
            self.event_mask_set(pulsectl.PulseEventMaskEnum.sink,
                pulsectl.PulseEventMaskEnum.sink_input)
            self.event_callback_set(self._callback)
            while not self._disconnect_evt.is_set():
                self.event_listen()
                if self.ev.facility == pulsectl.PulseEventFacilityEnum.sink:
                    self._on_pulse_sink_event()
                elif self.ev.facility == pulsectl.PulseEventFacilityEnum.sink_input:
                    self._on_pulse_sink_input_event()
        except KeyboardInterrupt: pass
        except pulsectl.pulsectl.PulseDisconnected: self.connect_async()
        
    def _callback(self, ev):
        self.ev = ev
        #print('Pulse event:', ev)
        raise pulsectl.PulseLoopStop

    def _on_pulse_sink_event(self):
        if self.ev.t == pulsectl.PulseEventTypeEnum.change:
            pass

    def _on_pulse_sink_input_event(self):
        new = self.sink_input_set()
        old = self._sink_input_set
        if self.ev.t == pulsectl.PulseEventTypeEnum.new:
            if not self.is_playing: self._events.on_start_playing()
            added = new.difference(old)
            self._sink_input_set = new
            self.is_playing.update(added)
        elif self.ev.t == pulsectl.PulseEventTypeEnum.remove:
            removed = old.difference(new)
            self._sink_input_set = new
            if not self.is_playing.intersection(removed): return
            self.is_playing.difference_update(removed)
            if not self.is_playing: self._events.on_stop_playing()


PulseListener.__name__ = "Pulse" # workaround for pulsectl

