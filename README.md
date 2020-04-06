# Freenon Network AVR Controlling Software
### Control your Denon AVR's power and master volume with your Ubuntu laptop or similar

## Requirements
- GNU OS (e.g. Ubuntu) or cygwin
- Python 3 and Pip
- Denon AVR compatible, connected via LAN/Wifi (tested with Denon X1400H)

**For automatic freenon_setup:**
- Private nameserver on LAN
- nmap and net-tools

**For freenon_daemon:**
- SystemD
- Pulseaudio


## Install

Install the requirements:
`sudo apt-get install python3-dev python3-pip nmap net-tools`

Cloning this repository in the current directory and installing via pip:
`$ git clone https://github.com/timojuez/denonavr.git freenon && pip3 install --user wheel && pip3 install --user ./freenon/ && rm -R ./freenon && freenon_setup`

If you do not have a nameserver in your LAN or freenon_setup cannot find your Denon device, set the 
host IP manually in the config file.

To uninstall: `pip3 uninstall freenon`


### Configuration
See configuration options in ~/.freenon.cfg and src/denon/freenon.cfg.default.

Note that this program is still in development and therefore start it with all sound output stopped and choose a maxvol way lower than 98.


## Usage

### Daemon
This connects the Pulseaudio volume controller to the Denon master volume, switches the AVR on and off when starting/suspending/resuming/shutdown.
`freenon_daemon`


### CLI and shortcuts
Plain commands can be sent to the AVR
`freenon_cmd [command]`

See the ./examples/*.sh.


## Development
It is possible to create a customised daemon that keeps your own program synchronised with the AVR.
See ./examples/custom_app.py


## Limitations
- Pulse daemon: The software volume currently stays the same as the hardware volume. When the software volume is at 50%, it sets the AVR volume to 50% and then you have 25% volume. Instead, software volume shall be at 100% and hardware volume 25% to save energy. This has to be fixed by implementing a separate volume control applet. As a workaround use a maxvol as low as you need! See config.
- This program is currently only controlling the sound channels alltogether. Controlling e.g. left and right channel separately is to be implemented.

