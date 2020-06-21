#!/usr/bin/env python3

from distutils.core import setup
from src import PKG_NAME


setup(name=PKG_NAME,
      version='1.5.19a',
      description='Network Amp Controlling Software',
      author='Timo Richter',
      author_email='timo.juez@gmail.com',
      url='https://github.com/timojuez/hificon',
      license='GNU General Public License v3 or later (GPLv3+)',
      packages=[PKG_NAME],
      package_dir={PKG_NAME: "src"},
      install_requires=["argparse"],
      extras_require={
        "autosetup": ["python-nmap", "netifaces"],
        "gnu_desktop": ["PyGObject","pycairo","pulsectl","pystray","Pillow"],
        "nongnu_desktop": ["pynput","pystray","Pillow"],
      },
      include_package_data=True,
      entry_points={'console_scripts': [
        'hifi_sh = %s.bin.shell:main'%PKG_NAME,
        'hificon = %s.bin.gui:main'%PKG_NAME,
        'hificon_setup = %s.bin.setup:main [autosetup]'%PKG_NAME,
        'hificon_mouse_binding = %s.bin.mouse_binding:main [nongnu_desktop]'%PKG_NAME,
      ]},
      scripts={'src/bin/hificon_key_event_handler'},
)

