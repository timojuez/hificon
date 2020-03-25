#!/usr/bin/env python3
import argparse, threading, time, pulsectl, signal, sys, socket
import dbus
from gi.repository import GLib, Gio
from denon import Denon


class IfConnected(object):
    """ with IfConnected(denon): 
        stops execution when connection lost, wait for reconnect and fire events
    """

    def __init__(self, denon):
        self.denon = denon
        
    def __enter__(self): pass

    def __exit__(self, type, value, traceback):
        if type not in (socket.timeout, socket.gaierror, socket.herror): return False
        sys.stderr.write("[Event] connection lost\n")
        sys.stderr.write("[Warning] dropping call\n")
        self.denon.wait_for_connection()
        sys.stderr.write("[Event] reconnected\n")
        pulse_c.on_reconnect()
        return True


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
        with ifConnected: 
            if self.denon.muted != pulsemuted: self.denon.muted = pulsemuted
            if not pulsemuted and self.denon.volume != avr_vol: self.denon.volume = avr_vol

    def updatePulseValues(self):
        """ Set pulse volume and mute according to AVR """
        self.denon.reset()
        with ifConnected: 
            avr_vol = self.denon.volume
            avr_muted = self.denon.muted
            pulse_vol = avr_vol/self.maxvol
            self.pulse.mute(self.pulse.sink_list()[self.sink],avr_muted)
            if not avr_muted: 
                self.pulse.volume_set_all_chans(
                    self.pulse.sink_list()[self.sink], pulse_vol)
                print("[Pulse] setting volume to %0.2f"%pulse_vol)
        
    def on_resume(self):
        """ Is being executed after resume from suspension """
        self.updatePulseValues()
        
    def on_reconnect(self):
        """ Execute when reconnected after connection aborted """
        self.updatePulseValues()
        

class PulseListener(PulseCommunicator):

    def __call__(self):
        print("[Event] Startup")
        if self.denon.poweron_wait() == 1: self.updateAvrValues()
        else: self.updatePulseValues() # AVR was already on
        
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
    
    def __init__(self, avr):
        self.denon = avr

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
            print("[Event] Suspend")
            with ifConnected: self.denon.poweroff()
        else: 
            print("[Event] Resume")
            self.denon.poweron_wait()
            pulse_c.on_resume()
    

class Main(object):
    
    def __init__(self):
        parser = argparse.ArgumentParser(description='Sync pulseaudio to Denon AVR')
        parser.add_argument('--host', type=str, metavar="IP", default=None, help='AVR IP or hostname. Default: auto detect')
        parser.add_argument('--maxvol', type=int, metavar="0..100", required=True, help='Equals 100%% volume in pulse')
        parser.add_argument('--no-power-control', default=False, action="store_true", help='Do not control the AVR power state and do not connect to system bus')
        parser.add_argument("-v",'--verbose', default=False, action='store_true', help='Verbose mode')
        self.args = parser.parse_args()
        
    def __call__(self):
        global pulse_c, ifConnected
        self.denon = Denon(self.args.host, verbose=self.args.verbose)
        ifConnected = IfConnected(self.denon)
        pulse_c = PulseCommunicator(self.denon,self.args.maxvol)
        if not self.args.no_power_control:
            signal.signal(signal.SIGTERM, self.on_shutdown)
            threading.Thread(target=DBusListener(self.denon)).start()
        threading.Thread(target=PulseListener(self.denon,self.args.maxvol)).start()

    def on_shutdown(self, sig, frame):
        print("[Event] Shutdown")
        with ifConnected: self.denon.poweroff()
        
    
if __name__ == "__main__":
    Main()()

