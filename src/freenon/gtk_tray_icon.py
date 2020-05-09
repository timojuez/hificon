#!/usr/bin/env python3
import argparse, sys
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import GLib, Gtk, Gdk
from .synctools import PluginInterface, EventHandler
try: 
    from .pulse import PulseListener, pulsectl
    from .pulse import PulseEventHandler as EventHandler
except ImportError: PulseListener = object


VOLUME_MAX = 60
VOLUME_DIFF = 3


class MyEventHandler(EventHandler):

    def on_connect(self):
        self.updatePluginValues()
        self.plugin.show()
        super(MyEventHandler,self).on_connect()

    def on_connection_lost(self):
        super(MyEventHandler,self).on_connection_lost()
        self.plugin.hide()


class FreenonPluginMixin(PluginInterface):
    volume = 0
        
    def getVolume(self):
        return self.volume
        
    def getMuted(self):
        return self.volume == 0
        
    def update_volume(self, volume):
        print(volume, file=sys.stderr)
        self.volume = volume
        self.updateIcon()
        
    def update_muted(self, muted):
        if muted:
            self.volume = 0
            self.updateIcon()
            
            
class Tray(FreenonPluginMixin):

    def __init__(self):
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
            self.icon.set_tooltip_text("Volume: %0.1f\n%s"%(self.volume,self.eh.denon.host))
            if self.volume == 0: 
                self.icon.set_from_icon_name("audio-volume-muted")
            else:
                icon_idx = int(round(float(self.volume)/VOLUME_MAX*(len(icons)-1)))
                self.icon.set_from_icon_name(icons[icon_idx])
        GLib.idle_add(do)
    
    def on_scroll(self, icon, event):
        if event.direction == Gdk.ScrollDirection.UP:
            volume = min(self.volume+VOLUME_DIFF,VOLUME_MAX)
            self.update_volume(volume)
            self.eh.on_plugin_change()
        elif event.direction == Gdk.ScrollDirection.DOWN:
            volume = max(0,self.volume-VOLUME_DIFF)
            self.update_volume(volume)
            self.eh.on_plugin_change()


class PulseSinkInputListener(PulseListener):
    def _on_pulse_sink_event(self): pass
    

class Main(object):
    
    def __init__(self):
        parser = argparse.ArgumentParser(description='AVR tray icon')
        parser.add_argument("-v",'--verbose', default=False, action='store_true', help='Verbose mode')
        self.args = parser.parse_args()
        
    def __call__(self):
        tray = Tray()
        eh = MyEventHandler(tray, verbose=self.args.verbose)
        tray.eh = eh
        if "pulsectl" in globals(): PulseSinkInputListener(eh)()
        eh.loop()
        

main = lambda:Main()()    
if __name__ == "__main__":
    main()

