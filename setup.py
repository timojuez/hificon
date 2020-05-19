#!/usr/bin/env python

from distutils.core import setup

setup(name='freenon',
      version='1.1.0a',
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
        "gi": ["PyGObject","pycairo"],
        "gnu_desktop": ["PyGObject","pycairo","filelock","pulsectl"],
        "nongnu_desktop": ["PyGObject","pycairo","pynput"],
      },
      include_package_data=True,
      entry_points={'console_scripts': [
        'freenon_cmd = freenon.denon:main',
        'freenon_gtk_tray_icon = freenon.gtk_tray_icon:main [gi]',
        'freenon_setup = freenon.setup:main [autosetup]',
        'freenon_key_event_handler = freenon.key_binding.key_event_handler:main [gnudesktop]',
        'freenon_mouse_binding = freenon.key_binding.mouse_binding:main [nongnu]',
      ]},
)

