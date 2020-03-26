#!/bin/bash -e
source `dirname $(readlink -f $0)`/include.sh

max=60


vol="$1"
if [ "$vol" -lt 0 ]; then vol=0; 
elif [ "$vol" -gt "$max" ]; then vol="$max";
fi

denon MV$vol

