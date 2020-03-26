#!/usr/bin/env python

from distutils.core import setup

setup(name='freenon',
      version='0.1',
      description='Free Denon Network AVR Controlling Software',
      author='Timo Richter',
      author_email='timo.juez@gmail.com',
      url='',
      license='GNU General Public License v3 or later (GPLv3+)',
      packages=['freenon'],
      package_dir={"": "src"},
      install_requires=[
        "wheel", "argparse", "pulsectl", "netifaces", "dbus-python", 
        "python-nmap", 
      ],
      include_package_data=True,
      entry_points={'console_scripts': [
        'freenon_cmd = src.freenon.denon:main',
        'freenon_daemon = src.freenon.daemon:main',
      ]},
)

