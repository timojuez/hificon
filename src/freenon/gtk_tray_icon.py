#!/usr/bin/env python3
import argparse, sys
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import GLib, Gtk, Gdk
from .synctools import EventHandler
try: 
    from .pulse import PulseListener, pulsectl
    from .pulse import PulseEventHandler as EventHandler
except ImportError: PulseListener = object


VOLUME_DIFF = 3


class Tray(EventHandler):

    def on_connect(self):
        self.plugin.show()
        super(MyEventHandler,self).on_connect()

    def on_connection_lost(self):
        super(MyEventHandler,self).on_connection_lost()
        self.plugin.hide()
        
    def on_avr_change(self, *args, **xargs):
        super(FreenonPluginMixin, self).on_avr_change(*args,**xargs)
        self.updateIcon()
            
    def __init__(self,*args,**xargs):
        super(Tray,self).__init__(*args,**xargs)
        self.icon = Gtk.StatusIcon()
        self.icon.connect("scroll-event",self.on_scroll)
        self.icon.set_visible(False)
        # no loop. EventHandler does it
        #loop = GLib.MainLoop(None)
        #loop.run()
    
    def show(self):
        GLib.idle_add(lambda:self.icon.set_visible(True))
        
    def hide(self):
        GLib.idle_add(lambda:self.icon.set_visible(False))
    
    def updateIcon(self):
        icons = ["audio-volume-low","audio-volume-medium","audio-volume-high"]
        def do():
            self.icon.set_tooltip_text("Volume: %0.1f\n%s"%(volume,self.denon.host))
            if muted:
                self.icon.set_from_icon_name("audio-volume-muted")
            else:
                icon_idx = int(round(float(volume)/maxvol*(len(icons)-1)))
                self.icon.set_from_icon_name(icons[icon_idx])
        try:
            volume = self.denon.volume
            muted = self.denon.muted
            maxvol = self.denon.maxvol
        except ConnectionError: pass
        else: GLib.idle_add(do)
    
    def on_scroll(self, icon, event):
        try:
            if event.direction == Gdk.ScrollDirection.UP:
                volume = min(self.volume+VOLUME_DIFF,self.denon.maxvol)
            elif event.direction == Gdk.ScrollDirection.DOWN:
                volume = max(0,self.volume-VOLUME_DIFF)
            self.denon.volume = volume
        except ConnectionError: pass
        else: self.updateIcon()
        

class PulseSinkInputListener(PulseListener):
    def _on_pulse_sink_event(self): pass
    

class Main(object):
    
    def __init__(self):
        parser = argparse.ArgumentParser(description='AVR tray icon')
        parser.add_argument("-v",'--verbose', default=False, action='store_true', help='Verbose mode')
        self.args = parser.parse_args()
        
    def __call__(self):
        tray = Tray(verbose=self.args.verbose)
        if "pulsectl" in globals(): PulseSinkInputListener(eh)()
        tray.loop()
        

main = lambda:Main()()    
if __name__ == "__main__":
    main()

