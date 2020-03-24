#!/usr/bin/env python3
import argparse, threading, time, pulsectl, signal
import dbus
from gi.repository import GLib, Gio
from denon import DenonSilentException as Denon


class PulseCommunicator(object):
    """
    Connects to pulseaudio and communicates with a Denon instance.
    Main task: volume control
    """
    sink = 0

    def __init__(self, avr, maxvol):
        self.denon = avr
        self.maxvol = maxvol
        self.pulse = pulsectl.Pulse("Freenon")
    
    def updateAvrValues(self):
        """ Set AVR volume and mute according to Pulse """
        sink = self.pulse.sink_list()[self.sink]
        pulsemuted = bool(sink.mute)
        avr_vol = round(sink.volume.value_flat*self.maxvol)
        if self.denon.muted != pulsemuted: self.denon.muted = pulsemuted
        if not pulsemuted: self.denon.volume = avr_vol

    def updatePulseValues(self):
        """ Set pulse volume and mute according to AVR """
        try:
            avr_vol = self.denon.getVolume()
            avr_muted = self.denon.muted
        except: return
        pulse_vol = avr_vol/self.maxvol
        self.pulse.volume_set_all_chans(
            self.pulse.sink_list()[self.sink], pulse_vol)
        #TODO self.pulse.muted = avr_muted
        print("[Pulse] setting volume to %0.2f"%pulse_vol)
        
    def on_resume(self):
        """ Is being executed after resume from suspension """
        self.updateAvrValues()
        

class PulseListener(PulseCommunicator):

    def __call__(self):
        self.updatePulseValues()
        #self.pulse.event_mask_set('all')
        self.pulse.event_mask_set(pulsectl.PulseEventMaskEnum.sink)
        self.pulse.event_callback_set(self.callback)
        while True:
            try: self.pulse.event_listen()
            except KeyboardInterrupt: return
            print("[Event] Pulseaudio change")
            self.updateAvrValues()

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
    
    def __init__(self, avr, pulse_c=None):
        self.denon = avr
        self.pulse_c = pulse_c
        print("[Event] Startup")
        self.denon.poweron_wait()

    def __call__(self):
        #dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        #self.session_bus = dbus.SessionBus()
        #self.system_bus = dbus.SystemBus()
        #session_bus.add_signal_receiver(
        #    self.poweron,'Resuming','org.freedesktop.UPower','org.freedesktop.UPower')

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
            print("[Event] Suspend")
            self.denon.poweroff()
        else: 
            print("[Event] Resume")
            self.denon.poweron_wait()
            if self.pulse_c: self.pulse_c.on_resume()
    

class Main(object):
    
    def __init__(self):
        parser = argparse.ArgumentParser(description='Sync pulseaudio to Denon AVR')
        parser.add_argument('--host', type=str, metavar="IP", default=None, help='AVR IP or hostname. Default: auto detect')
        parser.add_argument('--maxvol', type=int, metavar="0..100", required=True, help='Equals 100%% volume in pulse')
        parser.add_argument('--no-power-control', default=False, action="store_true", help='Do not control the AVR power state and do not connect to system bus')
        parser.add_argument("-v",'--verbose', default=False, action='store_true', help='Verbose mode')
        self.args = parser.parse_args()
        
    def __call__(self):
        self.denon = Denon(self.args.host, verbose=self.args.verbose)
        if not self.args.no_power_control:
            signal.signal(signal.SIGTERM, self.on_shutdown)
            pulse = PulseCommunicator(self.denon,self.args.maxvol)
            threading.Thread(target=DBusListener(self.denon,pulse)).start()
        threading.Thread(target=PulseListener(self.denon,self.args.maxvol)).start()

    def on_shutdown(self, sig, frame):
        print("[Event] Shutdown")
        self.denon.poweroff()
        
    
if __name__ == "__main__":
    Main()()

