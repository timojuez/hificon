#!/usr/bin/env python3
import argparse, sys
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('AppIndicator3', '0.1')
gi.require_version('Notify', '0.7')
from gi.repository import GLib, Gtk, Gdk
from gi.repository import AppIndicator3 as AppIndicator
from .. import Amp
from ..key_binding import VolumeService
from ..config import config


class Tray(object):

    def on_connect(self):
        self.updateIcon()
        self.show()

    def on_disconnected(self):
        self.hide()
        
    def on_amp_change(self, *args, **xargs):
        self.updateIcon()
            
    def __init__(self,*args,**xargs):
        self._volume = None
        self.scroll_delta = config.getfloat("GUI","tray_scroll_delta")
        self.icon = AppIndicator.Indicator.new("Freenon","Freenon",
            AppIndicator.IndicatorCategory.HARDWARE)
        self.icon.connect("scroll-event",self.on_scroll)
        self.icon.set_status(AppIndicator.IndicatorStatus.PASSIVE)
        self.amp = Amp(*args,
            on_connect=self.on_connect,
            on_disconnected=self.on_disconnected,
            on_change=self.on_amp_change,
            **xargs)
        #self.amp.loop()
        # no loop. EventHandler does it
        #loop = GLib.MainLoop(None)
        #loop.run()
    
    def show(self):
        GLib.idle_add(lambda:self.icon.set_status(AppIndicator.IndicatorStatus.ACTIVE))
        
    def hide(self):
        GLib.idle_add(lambda:self.icon.set_status(AppIndicator.IndicatorStatus.PASSIVE))
    
    def updateIcon(self):
        icons = ["audio-volume-low","audio-volume-medium","audio-volume-high"]
        def do():
            #self.icon.set_tooltip_text("Volume: %0.1f\n%s"%(volume,self.amp.host))
            if muted:
                self.icon.set_icon_full("audio-volume-muted","muted")
            else:
                icon_idx = int(round(float(volume)/maxvol*(len(icons)-1)))
                self.icon.set_icon_full(icons[icon_idx],str(volume))
        try:
            muted = self.amp.muted
            volume = 0 if muted else self.amp.volume
            maxvol = self.amp.maxvol
        except ConnectionError: pass
        else: GLib.idle_add(do)
    
    def on_scroll(self, icon, steps, direction):
        try:
            if direction == Gdk.ScrollDirection.UP:
                volume = self.amp.volume+self.scroll_delta*steps
            elif direction == Gdk.ScrollDirection.DOWN:
                volume = self.amp.volume-self.scroll_delta*steps
            else: return
            if self._volume == volume: return
            self._volume = volume
            self.amp.volume = volume
        except ConnectionError: pass
        else: self.updateIcon()
        

class Main(object):
    
    def __init__(self):
        parser = argparse.ArgumentParser(description='Freenon tray icon')
        parser.add_argument("-v",'--verbose', default=False, action='store_true', help='Verbose mode')
        self.args = parser.parse_args()
        
    def __call__(self):
        tray = Tray(verbose=self.args.verbose)
        try: VolumeService(verbose=self.args.verbose)()
        except OSError as e: print("[WARNING] VolumeService failed: %s"%repr(e))
        tray.amp.loop()
        

main = lambda:Main()()    
if __name__ == "__main__":
    main()

