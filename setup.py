#!/usr/bin/env python

import os
from distutils.core import setup

setup(name='hificon',
      version='1.5.3a',
      description='Network Amp Controlling Software',
      author='Timo Richter',
      author_email='timo.juez@gmail.com',
      url='',
      license='GNU General Public License v3 or later (GPLv3+)',
      packages=['hificon'],
      package_dir={"hificon": "src"},
      install_requires=["argparse"],
      extras_require={
        "autosetup": ["python-nmap", "netifaces"],
        "gnu_desktop": ["PyGObject","pycairo","pulsectl","pystray","Pillow"],
        "nongnu_desktop": ["pynput","pystray","Pillow"],
      },
      include_package_data=True,
      entry_points={'console_scripts': [
        'hifi_sh = hificon.bin.cmd:main',
        'hificon = hificon.bin.gtk:main',
        'hificon_setup = hificon.bin.setup:main [autosetup]',
        'hificon_mouse_binding = hificon.bin.mouse_binding:main [nongnu_desktop]',
      ]},
      scripts={'src/freenon/bin/hificon_key_event_handler'},
)

