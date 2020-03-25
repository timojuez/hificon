#!/usr/bin/env python3
import argparse, threading, time, pulsectl, signal, sys, socket
import dbus
from gi.repository import GLib, Gio
from denon import Denon


class DenonCustomPowerControl(Denon):
    
    def __init__(self, *args, no_poweron, no_poweroff, **xargs):
        super(DenonCustomPowerControl,self).__init__(*args,**xargs)
        if no_poweron: self.poweron = lambda:None
        if no_poweroff: self.poweroff = lambda:None
        

class IfConnected(object):
    """ with IfConnected(denon): 
        stops execution when connection lost, fire connection_lost event
    """

    def __init__(self, event_listener):
        self.el = event_listener
        
    def __enter__(self): pass

    def __exit__(self, type, value, traceback):
        if type not in (socket.timeout, socket.gaierror, socket.herror): return False
        self.el.on_connection_lost()
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
        
        
class EventListener(PulseCommunicator):

    def denon_connect_sync_wait(self):
        self.denon.wait_for_connection()
        if self.denon.running(): self.updatePulseValues()
        else:
            self.denon.poweron()
            self.updateAvrValues()

    def on_startup(self):
        """ program start """
        print("[Event] Startup")
        self.denon_connect_sync_wait()
        
    def on_shutdown(self, sig, frame):
        """ when shutting down computer """
        print("[Event] Shutdown")
        with ifConnected: self.denon.poweroff()
        
    def on_suspend(self):
        print("[Event] Suspend")
        with ifConnected: self.denon.poweroff()
    
    def on_resume(self):
        """ Is being executed after resume from suspension """
        print("[Event] Resume")
        self.denon_connect_sync_wait()
        
    def on_connection_lost(self):
        sys.stderr.write("[Event] connection lost\n")
        sys.stderr.write("[Warning] dropping call\n")
        self.denon.wait_for_connection()
        self.on_reconnect()
    
    def on_reconnect(self):
        """ Execute when reconnected after connection aborted """
        sys.stderr.write("[Event] reconnected\n")
        self.updatePulseValues()
        
    def on_pulseaudio_event(self):
        print("[Event] Pulseaudio change")
        self.updateAvrValues()
        

class PulseListener(EventListener):

    def __call__(self):
        #self.pulse.event_mask_set('all')
        self.pulse.event_mask_set(pulsectl.PulseEventMaskEnum.sink)
        self.pulse.event_callback_set(self.callback)
        while True:
            try: self.pulse.event_listen()
            except KeyboardInterrupt: return
            self.on_pulseaudio_event()

    def callback(self, ev):
        if not (ev.facility == pulsectl.PulseEventFacilityEnum.sink
            and ev.t == pulsectl.PulseEventTypeEnum.change): return
        #print('Pulse event:', ev)
        raise pulsectl.PulseLoopStop
    

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
    

class Main(object):
    
    def __init__(self):
        parser = argparse.ArgumentParser(description='Sync pulseaudio to Denon AVR')
        parser.add_argument('--host', type=str, metavar="IP", default=None, help='AVR IP or hostname. Default: auto detect')
        parser.add_argument('--maxvol', type=int, metavar="0..100", required=True, help='Equals 100%% volume in pulse')
        parser.add_argument('--no-power-on', default=False, action="store_true", help='Do not switch the AVR on when starting/resuming')
        parser.add_argument('--no-power-off', default=False, action="store_true", help='Do not switch the AVR off on suspend/shutdown')
        parser.add_argument("-v",'--verbose', default=False, action='store_true', help='Verbose mode')
        self.args = parser.parse_args()
        
    def __call__(self):
        global ifConnected
        denon = DenonCustomPowerControl(self.args.host, verbose=self.args.verbose, no_poweron=self.args.no_power_on,no_poweroff=self.args.no_power_off)
        el = EventListener(denon,self.args.maxvol)
        ifConnected = IfConnected(el)
        el.on_startup()
        
        signal.signal(signal.SIGTERM, el.on_shutdown)
        threading.Thread(target=DBusListener(el)).start()
        threading.Thread(target=PulseListener(denon,self.args.maxvol)).start()

    
if __name__ == "__main__":
    Main()()

