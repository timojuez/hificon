# HiFiCon Network Amplifier Server and Client Software
### This software provides high level Python variable bindings for an underlying asynchronous data transportation. It comes with three different client programs.


## Features
- HiFiCon Tray Control*
    - Control attributes via tray icon
    - Mouse and keyboard volume key support
    - Notifications OSD
    - Automatic amp power control
	    - Switching the amplifier on when sound starts playing**
	    - Switching the amplifier off when sound stops or computer shuts down/suspends
- HiFiCon Control Menu*
    - Control attributes in a standalone app
- HiFiSh HiFi Shell
    - Send custom commands and run your own hifi script
    - Record actions from remote control and repeat automatically
- Automatic amplifier discovery*
- Platform independent
- Easily control your AVR – even far away from remote control distance
- Amp server software

*Requires an implemented scheme

**Requires pulseaudio


## Preliminaries

- **A scheme** for communication is a plan that a server and client agree upon. It can be but not necessarily is a network protocol. Typically, different AVR manufacturers use their own scheme.
- **A target** is an entity that communicates using a scheme. A network amplifier can be a target.
- **A feature** is a variable that a target's scheme provides. It can be volume, power, etc.
- **A target URI** describes the connection to a target and has syntax `scheme:arg_0:...:arg_n`, where `scheme` is a class from ./src/schemes or of the form `[module.]scheme_class`. By default it is being read from the main.cfg. Example: `denon://192.168.1.5:23`
- A URI can carry a **query string** `?part_0&...&part_m` at the end which will be processed once initially according to the given order. If `part` has the form `feature=value`, the target's feature `feature` will be set to `value`. If `part` has the form `command` then `command` will be sent to the target. Example usage: `hifish -xt '?power=1&source=DVD&MVUP'`


### Supported Schemes

- Denon/Marantz AVR compatible (tested with Denon X1400H)
- Raw Telnet

For a complete list, run `hifish --help-schemes`


### Requirements on the Client
- Python 3 and Pip

**Amplifiers**
- The amplifier needs to be connected via LAN/Wifi

**For automatic power control:**
- SystemD
- Pulseaudio


### Requirements on Server
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

The menu lets you control all available features, e.g. sound mode, input, power, Audyssey settings, single speaker volume, etc. (depending on your target).

`python3 -m hificon.menu`



### HiFi Shell
HiFiSh is the HiFi Shell and it offers its own language called PyFiHiFi. PyFiHiFi is a Python dialect that is customised for programming with HiFiCon. It can read and write the target's features or run e.g. remote control actions (depending on the target).

#### Starting the shell
Calling `hifish` without arguments will start the prompt.
To execute a command from bash, call `hifish -c '[command]'`.
Hifi scripts can be executed by `hifish FILE.hifi`

See also `hifish -h` and the ./examples/.

#### High level commands
High level features are not scheme (resp. amp manufacturer) dependent and in the form `$feature` for reading and `$feature=value` for writing.
Examples: `$volume += 5`, `$source = 'DVD'`, `$power = True`
To see what features are being supported, type `help_features()` in hifish or call `hifish --help-features`

#### Raw commands
Raw commands can be sent to the target like `COMMAND`. If your command contains a space or special character (`;`) or if you need it's return value, use the alternative way `$"COMMAND"`. Examples: `MV50`, `PWON`, `$'PW?'`

#### PyFiHiFi Language
HiFiSh compiles the code into Python as described below. The Python code assumes the following:
```
import time
from hificon import Target
__return__ = None
__wait__ = .1
target = Target()
```

| HiFiSh | Python |
| --- | --- |
| `$"X"` or `$'X'` | `target.query("X", __return__); time.sleep(__wait__)` |
| `$X` | `target.X` |
| `wait(X)` | `time.sleep(X)` |

If `__return__` is a callable, `$""` will return the received line from the target where `__return__(line) == True`.

#### Script Creator
`python3 -m hificon.create_script`

The create_script tool helps to create HiFi scripts automatically or even to record remote control actions.

Example 1:
```
python3 -m hificon.create_script record --raw > my_script.hifi # start recording
# now change the target's values that you want to store
hifish my_script.hifi # repeat
```

Example 2:
```
python3 -m hificon.create_script -t emulate:denon full > example_script.hifi
```


### Server Software
You can implement an own scheme or protocol. Client and Server is being implemented into one single class. Inherit e.g. the class AbstractScheme or TelnetScheme. Pay attention to the methods `poll_feature` and `set_feature`.
Start the server by running `python3 -m hificon.server --target SCHEME_MODULE.CLASS`

If the prefix `emulate:` is being added to `--target`, a dummy server will be run for testing. You can connect to it using the clients mentioned above.

Examples:
- `python3 -m hificon.server --target denon://0.0.0.0:23`
- `python3 -m hificon.server --target emulate:denon://127.0.0.1:1234`


## Development

### Support for other devices
It is possible to implement the support e.g. for other AVR brands like Yamaha, Pioneer, Onkyo. It is easy to connect to any network device that communicates via telnet. See src/schemes/* as an example. See also "target" parameter in config and in hifish. Hint: `hifish --target raw_telnet://IP:PORT -f` prints all data received from `IP` via telnet.

### Reverse Engineering a Target
`hifish -f` opens a shell and prints all received data. Meanwhile change settings on the target e.g. with a remote and observe on what it prints. This may help you to program an own scheme.

### Custom Client Software
It is possible to create an own program that controls the target and keeps being synchronised with it.
See ./examples/custom_client.py

Your requirement will be the hificon package.


### AVR Emulator
For testing purposes, there is a server emulator software. Start it with `python3 -m hificon.server --target emulate:SCHEME`.

The Denon AVR software emulator acts nearly like the amp's Telnet service. Try it out: 
`python3 -m hificon.server --target emulate:denon://127.0.0.1:1234`
and connect to it e.g. via HiFiSh:
`hifish --target denon://127.0.0.1:1234`.

You can also emulate the HiFi Shell directly: `hifish --target emulate:denon`


## Troubleshoot
- If HiFiCon cannot find your device automatically, add its URI as "uri = SCHEME://IP:PORT" under [Target] to ~/.hificon/main.cfg in your user directory.
- If you are on a GNU OS and the key binding does not work, you can try the setup for proprietary OS.
- If your device lets you connect only once but you would like to run several HiFiCon programs at the same time, run `python3 -m hificon.server --target repeat:auto --listen-port 1234`. In the programs, set `localhost:1234` as your target.

