#!/usr/bin/env python3
from freenon.denon import Denon


def on_avr_change(attr, value):
    print("Changed %s to %s."%(attr,value))

if __name__ == "__main__":
    denon = Denon(on_avr_change=on_avr_change)
    denon.connect()
    print("Current volume: %.1f"%denon.volume)
    while True:
        newvol = input("Enter new volume: ")
        denon.volume = float(newvol)
        
