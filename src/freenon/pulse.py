#!/usr/bin/env python3
import argparse, pulsectl
from threading import Timer, Thread
from .synctools import PluginInterface, EventHandler
from .config import config


class AbstractPulse(object):
    def __init__(self): self.pulse = pulsectl.Pulse("Freenon")
    
    def pulse_is_playing(self):
        return len(self.pulse.sink_input_list()) > 0
    
    
class PulseEventHandler(EventHandler,AbstractPulse):

    def __init__(self, *args, **xargs):
        EventHandler.__init__(self, *args, **xargs)
        AbstractPulse.__init__(self)
        
    def on_connect(self):
        super(PulseEventHandler,self).on_connect()
        if self.pulse_is_playing():
            with self.denon.ifConnected: self.denon.poweron()


class PulsePluginRelative(AbstractPulse,PluginInterface):
    sink = 0

    def __init__(self):
        super(PulsePluginRelative,self).__init__()
        self.maxvol = config.getint("Pulse","maxvol")
    
    def getVolume(self):
        """ Set AVR volume and mute according to Pulse """
        sink = self.pulse.sink_list()[self.sink]
        volume = sink.volume.value_flat*self.maxvol
        return volume
        
    def getMuted(self):
        sink = self.pulse.sink_list()[self.sink]
        return bool(sink.mute)
        
    def update_volume(self, volume):
        pulsevol = self.pulse.sink_list()[self.sink].volume.value_flat
        self.maxvol = min(98,max(volume/max(0.01,pulsevol),10))
        print("[Pulse] 100%% := %02d"%self.maxvol)
    
    def update_muted(self, muted):
        self.pulse.mute(self.pulse.sink_list()[self.sink],muted)


class PulsePluginAbsolute(PulsePluginRelative):

    def update_volume(self, volume):
        if volume > self.maxvol: 
            self.maxvol = volume
            print("[Pulse] 100%% := %02d"%self.maxvol)
        volume = volume/self.maxvol
        self.pulse.volume_set_all_chans(
            self.pulse.sink_list()[self.sink], volume)
        print("[Pulse] setting volume to %0.2f"%volume)


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
            self.el.on_plugin_change()

    def _on_pulse_sink_input_event(self):
        if self.ev.t == pulsectl.PulseEventTypeEnum.new:
            print("[Pulse] start playing")
            if hasattr(self,"poweroff"): self.poweroff.cancel()
            with self.el.denon.ifConnected: self.el.denon.poweron()
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
        with self.el.denon.ifConnected: self.el.denon.poweroff()
        
    
class Main(object):
    
    def __init__(self):
        parser = argparse.ArgumentParser(description='Sync pulseaudio to Denon AVR')
        parser.add_argument("-v",'--verbose', default=False, action='store_true', help='Verbose mode')
        self.args = parser.parse_args()
        
    def __call__(self):
        PulsePlugin = PulsePluginAbsolute if config.getboolean("Pulse","absolute") else \
            PulsePluginRelative
        eh = PulseEventHandler(PulsePlugin(), verbose=self.args.verbose)
        PulseListener(eh).loop()


main = lambda:Main()()    
if __name__ == "__main__":
    main()

