# Freenon Network AVR Controlling Software
### Control your Denon AVR's power and master volume with your Ubuntu laptop or similar

## Requirements
- Denon/Marantz AVR compatible, connected via LAN/Wifi (tested with Denon X1400H)
- Python 3 and Pip
- Telnet

**For automatic freenon_setup:**
- Private nameserver on LAN
- nmap and net-tools

**For automatic power control:**
- SystemD
- Pulseaudio

**For mouse and keyboard volume key support**
- Xserver, macOS or Windows

**For the tray icon**
- GTK


## Install

Install the requirements:
`sudo apt-get install python3-dev python3-pip nmap net-tools python3-gi`

Cloning this repository in the current directory and installing via pip:
`$ git clone https://github.com/timojuez/denonavr.git freenon && pip3 install --user wheel && pip3 install --user ./freenon/[pulse,autosetup,gi] && rm -R ./freenon && freenon_setup`

If you do not have a nameserver in your LAN or freenon_setup cannot find your Denon device, set the 
host IP manually in the config file.

To uninstall: `pip3 uninstall freenon`


### Configuration
See configuration options in ~/.freenon.cfg and src/denon/freenon.cfg.default.

Note that this program is still in development and therefore try it with all sound output muted.


## Usage

### Method A: Gtk Tray Icon
This lets you control the volume by scrolling over a tray icon.
`freenon_gtk_tray_icon`
You may want to add the command to autostart.

To connect the mouse and keyboard volume keys to the AVR for the current user:
#### On Xorg
`freenon_setup --keys`
To undo, remove the lines after ## FREENON in ~/.xbindkeysrc and restart xbindkeys.

#### On other platforms
Setup: `pip3 install --user pynput`
To connect the extra mouse buttons, start `freenon_mouse_binding`. You may want to add the command to autostart.


### Method B: Synchronisation with Pulse
This connects the Pulseaudio volume controller to the Denon master volume, switches the AVR on and off when starting playback/idle/suspending/shutdown.
`freenon_pulse`

**Notice:** The software volume stays the same as the hardware volume. When the software volume is at 50%, it sets the AVR volume to 50% and then you have 25% volume. Instead, software volume shall be at 100% and hardware volume 25% to save energy. As a workaround, set maxvol in the config as low as you need or try method A!


### CLI and shortcuts
Plain commands can be sent to the AVR
`freenon_cmd [command]`

See the ./examples/*.sh.


## Development
It is possible to create a customised controller that keeps your own program synchronised with the AVR. Its dependency is freenon[gi] and optionally freenon[autosetup,pulse].
See ./examples/custom_app.py

If your development only relies on sending commands to the AVR, you need the class freenon.denon.Denon. Your requirement is purely the freenon package and optionally freenon[autosetup].


## Limitations
- This program is currently only controlling the sound channels alltogether. Controlling e.g. left and right channel separately is to be implemented.

