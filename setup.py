#!/usr/bin/env python

import os
from distutils.core import setup

setup(name='freenon',
      version='1.5.2a',
      description='Network Amp Controlling Software',
      author='Timo Richter',
      author_email='timo.juez@gmail.com',
      url='',
      license='GNU General Public License v3 or later (GPLv3+)',
      packages=['freenon'],
      package_dir={"": "src"},
      install_requires=["argparse"],
      extras_require={
        "autosetup": ["python-nmap", "netifaces"],
        "gnu_desktop": ["PyGObject","pycairo","pulsectl","pystray","Pillow"],
        "nongnu_desktop": ["pynput","pystray","Pillow"],
      },
      include_package_data=True,
      entry_points={'console_scripts': [
        'freenon_cmd = freenon.bin.cmd:main',
        'freenon_gtk = freenon.bin.gtk:main',
        'freenon_setup = freenon.bin.setup:main [autosetup]',
        'freenon_mouse_binding = freenon.bin.mouse_binding:main [nongnu_desktop]',
      ]},
      scripts={'src/freenon/bin/freenon_key_event_handler'},
)

