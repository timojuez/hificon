#!/usr/bin/env python

import os
from distutils.core import setup

setup(name='freenon',
      version='1.4.1a',
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
        "gi": ["PyGObject","pycairo"],
        "gnu_desktop": ["PyGObject","pycairo","pulsectl"],
        "nongnu_desktop": ["PyGObject","pycairo","pynput"],
      },
      include_package_data=True,
      entry_points={'console_scripts': [
        'freenon_cmd = freenon.bin.cmd:main',
        'freenon_gtk = freenon.bin.gtk:main [gi]',
        'freenon_setup = freenon.bin.setup:main [autosetup]',
        'freenon_mouse_binding = freenon.bin.mouse_binding:main [nongnu_desktop]',
      ]},
      scripts={'src/freenon/bin/freenon_key_event_handler'},
)

