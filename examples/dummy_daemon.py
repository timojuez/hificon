#!/usr/bin/env python3
from freenon.libdaemon import PluginInterface, EventHandler


class MyPlugin(PluginInterface):
    volume = 50
    muted = False
    
    def getVolume(self):
        return self.volume
        
    def getMuted(self): 
        return self.muted
        
    def update_volume(self, volume):
        print("[Plugin] volume changed to %d"%volume)
        self.volume = volume
        
    def update_muted(self, muted):
        print("[Plugin] muted changed to %s"%muted)
        self.muted = muted
        

if __name__ == "__main__":
    plugin = MyPlugin()
    eh = EventHandler(plugin)
    print("Current volume: %d"%plugin.volume)
    while True:
        newvol = input("Enter new volume: ")
        plugin.volume = int(newvol)
        eh.on_plugin_change()
        
