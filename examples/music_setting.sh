#!/bin/bash -e
if [ "$(freenon_cmd PW?)" != "PWON" ]; then
    freenon_cmd PWON
    sleep 3
fi
freenon_cmd 'DIM BRI' 'PSFRONT SPB' 'MSSTEREO' 'SISAT/CBL'

