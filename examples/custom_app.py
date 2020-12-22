#!/usr/bin/env python3
import time
from decimal import Decimal
from hificon.amp import features
from hificon import Amp


PROMPT = "Enter new volume: "

def on_feature_change(key, value, prev_value):
    name = amp.features[key].name

    if prev_value is None: # initial call
        print("Initially setting %s"%name)
    else:
        print("Changed %s to %s."%(name, value))
    print(PROMPT)
    
@features.require("volume") # this function uses amp.volume -> async call
def print_volume(amp):
    print("Current volume: %.1f"%amp.volume)
    print(PROMPT)

@features.require("volume") # this function uses amp.volume -> async call
def set_volume(amp, newvol):
    if newvol: amp.volume = Decimal(newvol)

if __name__ == "__main__":
    amp = Amp()
    amp.bind(on_feature_change=on_feature_change)
    with amp:
        amp.connect()
        print_volume(amp)
        while True:
            print(PROMPT)
            newvol = input()
            if newvol: set_volume(amp, newvol)

