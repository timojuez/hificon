#!/usr/bin/env python3
import time
from decimal import Decimal
from hificon.amp import features
from hificon import Amp


def on_feature_change(key, value, prev_value):
    if not key:
        print("Received unknown data: %s"%value)
        return

    name = amp.features[key].name

    if prev_value is None: # initial call
        print("Initially setting %s"%name)
    else:
        print("Changed %s to %s."%(name, value))

@features.require("volume") # this function uses amp.volume -> async call
def volume_prompt(amp):
    print("Current volume: %.1f"%amp.volume)
    while True:
        newvol = input("Enter new volume: ")
        if newvol: amp.volume = Decimal(newvol)

if __name__ == "__main__":
    amp = Amp()
    amp.bind(on_feature_change=on_feature_change)
    with amp:
        amp.connect()
        volume_prompt(amp)
        while True: time.sleep(1)

