#!/usr/bin/env python

from distutils.core import setup

setup(name='freenon',
      version='0.2a',
      description='Network AVR Controlling Software',
      author='Timo Richter',
      author_email='timo.juez@gmail.com',
      url='',
      license='GNU General Public License v3 or later (GPLv3+)',
      packages=['freenon'],
      package_dir={"": "src"},
      install_requires=[
        "argparse", "pulsectl", "netifaces", "dbus-python", 
        "python-nmap", 
      ],
      include_package_data=True,
      entry_points={'console_scripts': [
        'freenon_cmd = freenon.denon:main',
        'freenon_daemon = freenon.daemon:main',
        'freenon_setup = freenon.setup:main',
      ]},
)

