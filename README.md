# HiFiCon Network Amp Software
### Free High Freedelity for Your Computer

## Features
- HiFiCon Tray Control*
    - Amplifier control via tray icon
    - Mouse and keyboard volume key support
    - Amplifier notifications OSD
    - Automatic amp power control
	    - Switching the amplifier on when sound starts playing**
	    - Switching the amplifier off when sound stops or computer shuts down/suspends
- HiFiCon Control Menu*
    - Manipulate many of the amp's attributes
- HiFiSh HiFi Shell: Send custom commands to the amp and program your own hifi script
- Automatic amplifier discovery*
- Platform independent
- Easily control your AVR – even far away from remote control distance
- Amp server software

*Currently only supports Denon/Marantz AVR compatible (tested with Denon X1400H)

**Requires pulseaudio


## Requirements on the Client
- Amplifier connected via LAN/Wifi
- Python 3 and Pip

Optional:

**For automatic power control:**
- SystemD
- Pulseaudio

**For mouse and keyboard volume key support**
- Any platform

## Requirements on Server
- Python 3 and Pip


## Install

### Ubuntu and other GNU OS
Install the requirements:

`sudo apt-get install python3-dev python3-pip python3-gi`

Cloning this repository in the current directory and installing via pip:

`$ git clone https://github.com/timojuez/hificon.git hificon && pip3 install --user wheel && pip3 install --user ./hificon/[gnu_desktop] && rm -R ./hificon && python3 -m hificon`

### Proprietary OS
On Mac/Windows, download and install Python3 with Pip.
Then execute:

`$ git clone https://github.com/timojuez/hificon.git hificon && pip3 install --user wheel && pip3 install --user ./hificon/[nongnu_desktop] && rm -R ./hificon && python3 -m hificon`

To connect the extra mouse buttons, start `hificon_mouse_binding`. You may want to add the command to autostart.

### Uninstall
To uninstall: `pip3 uninstall hificon`

Ggf remove the lines after ## HIFICON in ~/.xbindkeysrc and restart xbindkeys.


### Configuration
See configuration options in ~/.hificon/main.cfg and src/share/main.cfg.default.


## Usage

Note that this program is still in development and therefore try it first with all sound output stopped.

### Tray Control
Start the HiFi Icon:
`python3 -m hificon.tray`


### Control Menu

The menu lets you control all available amplifier attributes, e.g. sound mode, input, power, Audyssey settings, single speaker volume, etc. (depending on your amp).

`python3 -m hificon.menu`



### HiFi Shell
HiFiSh is the HiFi Shell and it offers its own language called PyFiHiFi. PyFiHiFi is a Python dialect that is customised for amplifier programming. It can read and write the amp's attributes or run remote control actions.

#### Starting the shell
Calling `hifish` without arguments will start the prompt.
To execute a command from bash, call `hifish -c '[command]'`.
Hifi scripts can be executed by `hifish FILE.hifi`

See also `hifish -h` and the ./examples/.

#### High level commands
High level attributes are not protocol (resp. amp manufacturer) specific and start with a `$`. 
Example: `$volume=40`
To see what attributes are being supported, type `help()` or call `hifish --protocol .emulator -c 'help()'`

#### Raw commands
Raw commands can be sent to the amp like `MV50` or `PWON`. If your command contains a space or special character (`;`) or if you need it's return value, use the alternative way `$"COMMAND"`. 

#### PyFiHiFi Language
HiFiSh compiles the code into Python as described below. The Python code assumes the following:
```
import time
from hificon import Amp
__return__ = None
__wait__ = .1
amp = Amp()
```

| HiFiSh | Python |
| --- | --- |
| `$"X"` or `$'X'` | `amp.query("X", __return__); time.sleep(__wait__)` |
| `$X` | `amp.X` |
| `wait(X)` | `time.sleep(X)` |

If `__return__` is a callable, `$""` will return the received line from the amp where `__return__(line) == True`.


### Server Software
You can implement an own protocol and start the server by running `python3 -m hificon.telnet_server --listen-host 0.0.0.0 --listen-port 23 --protocol PROTOCOL.MODULE`

The switch `-e` starts a dummy server for testing. You can connect to it using the clients mentioned above.


## Development

### Support for other AVR brands
It is possible to implement the support for other AVR brands like Yamaha, Pioneer, Onkyo. This software can connect your computer to any network amp that communicates via telnet. See src/protocol/* as an example. See also "protocol" parameter in config and in hifish. Hint: `hifish --protocol .raw_telnet -f --host [IP]` prints all data received from [IP] via telnet.

### Reverse Engineering Amplifiers
`hifish -f` opens a shell and prints all received data from the amp. Meanwhile change settings e.g. with a remote and observe on what it prints. This may help you to program an own protocol.

### Custom Amp Control Software
It is possible to create an own program that controls the amp and keeps being synchronised with it.
See ./examples/custom_app.py

Your requirement is purely the hificon package.


### AVR Emulator
For testing purposes, there is a Denon AVR software emulator that nearly acts like the amp's Telnet protocol. Try it out by starting the emulator `python3 -m hificon.telnet_server -e --listen-port [port] --protocol .denon` and connect to it e.g. via the HiFiShell `hifish --protocol .denon --host 127.0.0.1 --port [port]`.

You can also emulate the HiFi Shell: `hifish --protocol .emulator`


## Troubleshoot
- If HiFiCon cannot find your device, add the amp's IP address as "Host = [IP]" under [Amp] to ~/.hificon/main.cfg in your user directory.
- If you are on a GNU OS and the key binding does not work, you can try the setup for proprietary OS.
- If your device lets you connect only once but you would like to run several HiFiCon programs at the same time, run `python3 -m hificon.telnet_server -r --protocol .auto --listen-port 1234`. In the programs, set `localhost:1234` as your amp.

