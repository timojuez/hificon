# Freenon - Free Denon Network AVR Controlling Software for GNU
### Control power and master volume with your Ubuntu laptop or similar

## Requirements
- GNU OS (e.g. Ubuntu) or cygwin
- Python 3
- Denon AVR compatible, connected via LAN/Wifi (tested with Denon X1400H)
- Network connection


## Install

Install the python3 development package:
`sudo apt-get install python3-dev`

Clone or download this repository in the current directory and execute
`$ pip3 install --user wheel && pip3 install --user .`

## Usage

### Daemon
This connects the Pulseaudio volume controller to the Denon master volume, switches the AVR on and off when starting/suspending/resuming/shutdown.
`freenon_daemon --maxvol 50`

See configuration options in ~/.freenon.cfg and src/denon/freenon.cfg.default.

Note that this program is still in development and therefore start it with all sound output stopped and choose a --maxvol way lower than 100.


### CLI and shortcuts
Plain commands can be sent to the AVR
`freenon_cmd [command]`

See the ./examples.


## Limitations
- Pulse volume is being forwarded to AVR but not vice versa
- The software volume currently stays the same as the hardware volume. When the software volume is at 50%, it sets the AVR volume to 50% and then you have 25% volume. Instead, software volume shall be at 100% and hardware volume 25% to save energy. This has to be fixed in a future version. As a workaround use a --maxvol as low as you need!
- This program is currently only controlling the sound channels alltogether. Controlling e.g. left and right channel separately is to be implemented.

