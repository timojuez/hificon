#!/usr/bin/env python3
import time
from decimal import Decimal
from hificon import Target


PROMPT = "Enter new volume: "


def on_feature_change(key, value):
    name = target.features[key].name
    print("Changed %s to %s."%(name, value))
    print(PROMPT)
    

def print_volume():
    print("Current volume: %.1f"%target.volume)
    print(PROMPT)


if __name__ == "__main__":
    #target = Target()
    ## for testing:
    target = Target("emulator:denon")

    target.features.volume.bind(on_set = lambda: print("Initially setting volume"))
    target.bind(on_feature_change = on_feature_change)
    with target:
        target.connect()
        target.schedule(print_volume, requires=("volume",)) # this function needs target.volume -> schedule call
        while True:
            print(PROMPT)
            newvol = input()
            if newvol: target.volume = Decimal(newvol)

