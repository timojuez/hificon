#!/usr/bin/env python3

import os
from distutils.core import setup


script_dir = os.path.dirname(os.path.realpath(__file__))
with open(f"{script_dir}/src/info.py") as fp: exec(fp.read())

setup(name=PKG_NAME,
      version=VERSION,
      description='Network Amp Controlling Software',
      author=AUTHOR,
      author_email='timo.juez@gmail.com',
      url=URL,
      packages=[PKG_NAME],
      package_dir={PKG_NAME: "src"},
      install_requires=["argparse"],
      extras_require={
        "gnu_desktop": ["PyGObject","pycairo","pynput","pulsectl","kivy"],
        "nongnu_desktop": ["PyGObject","pycairo","pynput","kivy"],
      },
      include_package_data=True,
      entry_points={'console_scripts': [
        'hifish = %(name)s.hifish:main'%dict(name=PKG_NAME),
        "%(name)s_server = %(name)s.server:main"%dict(name=PKG_NAME),
        "%(name)s_menu = %(name)s.menu:main"%dict(name=PKG_NAME),
        '%(name)s_tray = %(name)s.tray:main'%dict(name=PKG_NAME),
        '%(name)s_setup = %(name)s.tray.setup:main'%dict(name=PKG_NAME),
      ]},
)

