import pulsectl, time, sys
from threading import Thread


class ConnectedPulse(pulsectl.Pulse):

    def __init__(self,*args,**xargs):
        super().__init__(*args,connect=False,**xargs)
        self.connect_pulse()

    def connect_pulse(self):
        def connect():
            self.connect()
            self.on_connected()
        def keep_reconnecting():
            while True:
                try: connect()
                except pulsectl.pulsectl.PulseError: time.sleep(3)
                else: break
        print("[%s] Connecting..."%self.__class__.__name__, file=sys.stderr)
        try: connect()
        except pulsectl.pulsectl.PulseError:
            Thread(target=keep_reconnecting,daemon=True).start()
    
    def on_connected(self):
        print("[%s] Connected to Pulseaudio."%self.__class__.__name__, file=sys.stderr)
    
    
class PulseListener(ConnectedPulse):
    """ Listen for pulseaudio change events """
    
    def __init__(self, event_listener):
        self.is_playing = False
        self._events = event_listener
        super().__init__("Freenon")

    def _is_playing(self):
        try: return len(self.sink_input_list()) > 0
        except:
            if not self.connected: raise pulsectl.pulsectl.PulseDisconnected()
            raise
    
    def on_connected(self):
        # Pulseaudio connected
        super().on_connected()
        try: self.is_playing = self._is_playing()
        except pulsectl.pulsectl.PulseDisconnected: return self.connect_pulse() 
        Thread(target=self.loop, name=self.__class__.__name__, daemon=True).start()
        
    def loop(self):
        try:
            #self.event_mask_set('all')
            self.event_mask_set(pulsectl.PulseEventMaskEnum.sink,
                pulsectl.PulseEventMaskEnum.sink_input)
            self.event_callback_set(self._callback)
            while True:
                self.event_listen()
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
        self.is_playing = self._is_playing()
        if self.ev.t == pulsectl.PulseEventTypeEnum.new:
            self._events.on_start_playing()
        elif self.ev.t == pulsectl.PulseEventTypeEnum.remove and not self.is_playing:
            self._events.on_stop_playing()


PulseListener.__name__ = "Pulse" # workaround for pulsectl

