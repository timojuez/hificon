#!/bin/bash -e
if [ "$(freenon_cmd PW?)" != "PWON" ]; then
    freenon_cmd PWON
    sleep 3
fi

# Switch Bass Mode
if [ "$(freenon_cmd "PSFRONT?")" != "PSFRONT SPB" ]; then
    freenon_cmd 'MNMEN OFF' 'MNMEN ON' MNCUP MNCUP MNCUP MNCUP MNCUP MNCUP MNCUP MNCDN MNCDN MNCDN MNENT MNCDN MNENT MNCDN MNCDN MNCDN MNCDN MNCDN MNENT MNENT MNCRT MNENT 
    sleep 2
    freenon_cmd 'MNMEN OFF'
fi

freenon_cmd 'DIM BRI' 'PSFRONT SPB' 'SISAT/CBL' 'MSSTEREO' 'PSMULTEQ:OFF'
sleep 1
freenon_cmd 'CVSW 50'

