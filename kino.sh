#!/bin/bash -e
source `dirname $(readlink -f $0)`/include.sh

if [ "$(denon PW?)" != "PWON" ]; then
    denon PWON
    sleep 3
fi
denon 'PSFRONT SPA' 'MSDOLBY DIGITAL' 'SISAT/CBL'

