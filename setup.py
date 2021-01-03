#!/usr/bin/env python3

from distutils.core import setup
from src import PKG_NAME, VERSION, AUTHOR, URL


setup(name=PKG_NAME,
      version=VERSION,
      description='Network Amp Controlling Software',
      author=AUTHOR,
      author_email='timo.juez@gmail.com',
      url=URL,
      license='GNU General Public License v3 or later (GPLv3+)',
      packages=[PKG_NAME],
      package_dir={PKG_NAME: "src"},
      install_requires=["argparse"],
      extras_require={
        "gnu_desktop": ["PyGObject","pycairo","pulsectl","kivy"],
        "nongnu_desktop": ["PyGObject","pycairo","pynput","kivy"],
      },
      include_package_data=True,
      entry_points={'console_scripts': [
        'hifish = %(name)s.hifish:main'%dict(name=PKG_NAME),
        "%(name)s_telnet_server = %(name)s.telnet_server:main"%dict(name=PKG_NAME),
        "%(name)s_menu = %(name)s.menu:main"%dict(name=PKG_NAME),
        '%(name)s = %(name)s.tray:main'%dict(name=PKG_NAME),
        '%(name)s_setup = %(name)s.tray.setup:main'%dict(name=PKG_NAME),
        '%(name)s_mouse_binding = %(name)s.tray.mouse_binding:main [nongnu_desktop]'%dict(name=PKG_NAME),
      ]},
)

