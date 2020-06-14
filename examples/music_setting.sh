#!/bin/bash -e
if [ "$(hifi_sh PW?)" != "PWON" ]; then
    hifi_sh PWON
    sleep 3
fi

# Switch Bass Mode
if [ "$(hifi_sh --return PSFRONT "PSFRONT?")" != "PSFRONT SPB" ]; then
    hifi_sh 'MNMEN OFF' 'MNMEN ON' MNCUP MNCUP MNCUP MNCUP MNCUP MNCUP MNCUP MNCDN MNCDN MNCDN MNENT MNCDN MNENT MNCDN MNCDN MNCDN MNCDN MNCDN MNENT MNENT MNCRT MNENT 
    sleep 2
    hifi_sh 'MNMEN OFF'
fi

hifi_sh 'DIM BRI' 'PSFRONT SPB' 'SISAT/CBL' 'MSSTEREO' 'PSMULTEQ:OFF'
sleep 1
hifi_sh 'CVSW 50'

