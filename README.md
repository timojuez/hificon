# Freenon - Free Denon Network AVR Controlling Software for GNU
### Control power and master volume with your Ubuntu laptop or similar

## Install

### Requirements
- GNU OS (e.g. Ubuntu) or cygwin
- Python 3
- Denon AVR compatible (tested with X1400H)
- Network connection

## Daemon
This connects the Pulseaudio volume controller to the Denon master volume, switches the AVR on and off when starting/suspending/resuming/shutdown.
`./daemon --maxvol 50`

Note that this program is still in development and therefore start it with all sound output stopped and choose a --maxvol way lower than 100.


## CLI
Plain commands can be sent to the AVR
`./denon.py [command]`

See the .sh scripts for examples.

## Limitations
This program is currently only controlling the sound channels alltogether. Controlling e.g. left and right channel separately is to be implemented.

