#!/usr/bin/env python

from distutils.core import setup

setup(name='freenon',
      version='1.3.1a',
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
      """
      entry_points={'console_scripts': [
        'freenon_gtk = freenon.freenon_gtk:main [gi]',
        'freenon_setup = freenon.setup:main [autosetup]',
        'freenon_key_event_handler = freenon.key_binding.key_event_handler:main',
        'freenon_mouse_binding = freenon.key_binding.mouse_binding:main [nongnu_desktop]',
      ]},
      """
      scripts=map(lambda e:"bin/%s"%e, os.listdir("bin")),
)

