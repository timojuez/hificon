#!/usr/bin/env python3
from hificon import Amp


def on_amp_change(attr, value):
    print("Changed %s to %s."%(attr,value))

def volume_prompt():
    print("Current volume: %.1f"%amp.volume)
    while True:
        newvol = input("Enter new volume: ")
        amp.volume = float(newvol)

if __name__ == "__main__":
    amp = Amp()
    amp.bind(on_change=on_amp_change, on_connect=volume_prompt)
    amp.mainloop()

