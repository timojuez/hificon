#!/usr/bin/env python

from distutils.core import setup

setup(name='freenon',
      version='0.7.2a',
      description='Network AVR Controlling Software',
      author='Timo Richter',
      author_email='timo.juez@gmail.com',
      url='',
      license='GNU General Public License v3 or later (GPLv3+)',
      packages=['freenon'],
      package_dir={"": "src"},
      install_requires=["argparse"],
      extras_require={
        "autosetup": ["python-nmap", "netifaces"],
        "pulse": ["pulsectl"],
        "gi": ["PyGObject","pycairo"],
      },
      include_package_data=True,
      entry_points={'console_scripts': [
        'freenon_cmd = freenon.denon:main',
        'freenon_pulse = freenon.pulse:main [pulse,gi]',
        'freenon_gtk_tray_icon = freenon.gtk_tray_icon:main [pulse,gi]',
        'freenon_setup = freenon.setup:main [autosetup]',
        'freenon_key_event_handler = freenon.key_event_handler:main',
      ]},
)

