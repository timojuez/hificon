#!/usr/bin/env python3
from hificon import Amp


def on_feature_change(key, value, *args):
    print("Changed %s to %s."%(key,value))

def volume_prompt():
    print("Current volume: %.1f"%amp.volume)
    while True:
        newvol = input("Enter new volume: ")
        amp.volume = float(newvol)

if __name__ == "__main__":
    amp = Amp()
    amp.bind(on_feature_change=on_feature_change, on_connect=volume_prompt)
    amp.mainloop()

