#!/usr/bin/env python3
import time
from decimal import Decimal
from hificon import Target


PROMPT = "Enter new volume: "


def on_receive_feature_value(f, value):
    print("Changed %s to %s."%(f.name, value))
    print(PROMPT)


def print_volume(volume):
    print("Current volume: %.1f"%volume.get())
    print(PROMPT)


if __name__ == "__main__":
    #target = Target()
    ## for testing:
    target = Target("emulate:denon")

    target.features.volume.bind(on_set = lambda: print("Initially setting volume"))
    target.bind(on_receive_feature_value = on_receive_feature_value)
    with target:
        target.connect()
        target.schedule(print_volume, requires=("volume",)) # this function needs target.volume -> schedule call
        while True:
            print(PROMPT)
            newvol = input()
            if newvol: target.features.volume.remote_set(Decimal(newvol))

