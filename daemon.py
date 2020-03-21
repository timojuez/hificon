#!/usr/bin/env python3
# Denonziant, Denuntu, 

import dbus
from gi.repository import GLib
from denon import Denon

MAXVOL = 70
DENON_IP = None # automatic


class PulseListener(object):
    """
    Connects to pulseaudio and communicates with a Denon instance.
    Main task: volume control
    """

    def __init__(self, denon):
        self.denon = denon
        with pulsectl.Pulse('event-printer') as pulse:
            self.pulse = pulse
            # print('Event types:', pulsectl.PulseEventTypeEnum)
            # print('Event facilities:', pulsectl.PulseEventFacilityEnum)
            # print('Event masks:', pulsectl.PulseEventMaskEnum)

            #pulse.event_mask_set('all')
            pulse.event_mask_set(pulsectl.PulseEventMaskEnum.sink)
            pulse.event_callback_set(self.callback)
            while True:
                try: pulse.event_listen()
                except KeyboardInterrupt: pass
                sink = self.pulse.sink_list()[0]
                volume = round(sink.volume.value_flat*MAXVOL)
                muted = sink.mute
                denon("MUON" if muted else "MUOFF")
                if not muted: denon("MV%d"%volume)

    def callback(self, ev):
        if not (ev.facility == pulsectl.PulseEventFacilityEnum.sink
            and ev.t == pulsectl.PulseEventTypeEnum.change): return
        #print('Pulse event:', ev)
        raise pulsectl.PulseLoopStop
    

class DBusListener(object):
    """
    Connects to DBus and communicates with a Denon instance.
    Main tasks: Power on on wifi connection, power off on standby
    """
    
    def __init__(self):
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        self.session_bus = dbus.SessionBus()
        self.system_bus = dbus.SystemBus()
        #session_bus.add_signal_receiver()

    def __call__(self):
        loop = GLib.MainLoop()
        loop.run()
        

if __name__ == "__main__":
    avr = Denon(DENON_IP)
    PulseListener(avr)
    
