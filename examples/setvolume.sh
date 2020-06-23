#!/bin/bash -e
max=60


vol="$1"
if [ "$vol" -lt 0 ]; then vol=0; 
elif [ "$vol" -gt "$max" ]; then vol="$max";
fi

hifi_sh -c MV$vol

