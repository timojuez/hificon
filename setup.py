#!/usr/bin/env python3

from distutils.core import setup
from src import PKG_NAME, VERSION


setup(name=PKG_NAME,
      version=VERSION,
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
        "gnu_desktop": ["PyGObject","pycairo","pulsectl","Pillow","wxPython"],
        "nongnu_desktop": ["pynput","Pillow","wxPython"],
      },
      include_package_data=True,
      entry_points={'console_scripts': [
        'hifi_sh = %(name)s.bin.hifish:main'%dict(name=PKG_NAME),
        "%(name)s_amp_emulator = %(name)s.bin.amp_emulator:main"%dict(name=PKG_NAME),
        '%(name)s = %(name)s.bin.main:main'%dict(name=PKG_NAME),
        '%(name)s_setup = %(name)s.bin.setup:main [autosetup]'%dict(name=PKG_NAME),
        '%(name)s_mouse_binding = %(name)s.bin.mouse_binding:main [nongnu_desktop]'%dict(name=PKG_NAME),
      ]},
      scripts={'src/bin/hificon_key_event_handler'},
)

