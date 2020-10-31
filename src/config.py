# -*- coding: utf-8 -*- 

import os, configparser, pkgutil
from decimal import Decimal
from . import PKG_NAME

FILE=os.path.expanduser("~/.%s.cfg"%PKG_NAME)


class ExtendedConfigParser(configparser.ConfigParser):
    
    def __init__(self,*args,**xargs):
        super().__init__(*args, converters={'decimal': Decimal}, **xargs)
        
    def clear_sections(self):
        for s in self.sections(): self[s].clear()
        
    def getlist(self, section, option):
        return list(map(lambda s:s.strip(), self[section][option].split(",")))
        
    def setlist(self, section, option, value):
        self[section][option] = ", ".join(value)


class ConfigDiffParser(ExtendedConfigParser):
    """ Append modified values to @local_path """
    
    def __init__(self,local_path,*args,**xargs):
        super().__init__(*args,**xargs)
        self._local_path = local_path
        self._local = ExtendedConfigParser()
        self._local.read([local_path])
        
    def set(self, section, *args, **xargs):
        super().set(section, *args, **xargs)
        if section not in self._local.sections(): self._local.add_section(section)
        self._local.set(section, *args, **xargs)
        self.save()
    
    def __setitem__(self, section, *args, **xargs):
        super().__setitem__(section, *args, **xargs)
        if section not in self._local.sections(): self._local.add_section(section)
        self._local.set(section, *args, **xargs)
        self.save()
    
    def save(self):
        with open(self._local_path,"w") as f:
            self._local.write(f)


default = pkgutil.get_data(__name__,"share/hificon.cfg.default").decode()
config = ConfigDiffParser(FILE)
config.read_string(default)
config.read([FILE])

