# -*- coding: utf-8 -*- 

import os, configparser, pkgutil

FILE=os.path.expanduser("~/.freenon.cfg")


class MyConfigParser(configparser.ConfigParser):
    
    def clear_sections(self):
        for s in self.sections(): self[s].clear()
    
    def save(self):
        with open(FILE,"w") as f:
            self.write(f)


config = MyConfigParser()
default = pkgutil.get_data(__name__,"share/freenon.cfg.default").decode()
config.read_string(default)
config.read([
    FILE
])

