#!/bin/bash -e
if [ "$(hifi_sh -c '$power')" ]; then
    hifi_sh -c PWON
    sleep 3
fi

# Switch Bass Mode
if [ "$(hifi_sh --return PSFRONT -c "PSFRONT?")" != "PSFRONT SPA" ]; then
    hifi_sh -c 'MNMEN OFF' 'MNMEN ON' MNCUP MNCUP MNCUP MNCUP MNCUP MNCUP MNCUP MNCDN MNCDN MNCDN MNENT MNCDN MNENT MNCDN MNCDN MNCDN MNCDN MNCDN MNENT MNENT MNCRT MNENT 
    sleep 2
    hifi_sh -c 'MNMEN OFF'
fi

hifi_sh -c 'DIM DAR' 'PSFRONT SPA' 'SISAT/CBL' 'MSDTS SURROUND' 'PSMULTEQ:AUDYSSEY' #'MSDOLBY DIGITAL'
sleep 1
hifi_sh -c 'CVSW 465'

