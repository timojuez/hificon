#!/usr/bin/env python3
from freenon import Denon


def on_avr_change(attr, value):
    print("Changed %s to %s."%(attr,value))

def volume_prompt():
    print("Current volume: %.1f"%denon.volume)
    while True:
        newvol = input("Enter new volume: ")
        denon.volume = float(newvol)

if __name__ == "__main__":
    denon = Denon(on_avr_change=on_avr_change, on_connect=volume_prompt)
    denon.loop()
