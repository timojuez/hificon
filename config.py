# -*- coding: utf-8 -*- 

import os, configparser

FILE=os.path.expanduser("~/.freenon.cfg")


class MyConfigParser(configparser.ConfigParser):
    
    def save(self):
        with open(FILE,"w") as f:
            self.write(f)
            
            
script_dir = os.path.dirname(os.path.abspath(__file__))
config = MyConfigParser()
config.read([
    os.path.join(script_dir,"freenon.cfg.default"), 
    FILE
])


