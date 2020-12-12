# -*- coding: utf-8 -*- 

import os, configparser, pkgutil, json
from collections import UserDict
from decimal import Decimal
from .. import PKG_NAME

CONFDIR = os.path.expanduser("~/.%s"%PKG_NAME)
FILE = os.path.join(CONFDIR, "main.cfg")


class ExtendedConfigParser(configparser.ConfigParser):
    
    def __init__(self,*args,**xargs):
        super().__init__(*args, converters={'decimal': Decimal}, **xargs)
        
    def clear_sections(self):
        for s in self.sections(): self[s].clear()
        
    def setboolean(self, section, option, value):
        self[section][option] = "yes" if value else "no"
        
    def getlist(self, section, option):
        return list(map(lambda s:s.strip(), self[section][option].split(",")))
        
    def setlist(self, section, option, value):
        self[section][option] = ", ".join(value)
        
    def getdict(self, section, option):
        return json.loads(self[section][option])
        
    def setdict(self, section, option, value):
        self[section][option] = json.dumps(value)


class ConfigDiffMixin:
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


class ShortcutsMixin:
    volume = property(lambda self: self.get("Amp","volume_feature_key"))
    muted = property(lambda self: self.get("Amp","muted_feature_key"))
    power = property(lambda self: self.get("Amp","power_feature_key"))
    source = property(lambda self: self.get("Amp","source_feature_key"))


class ConfigParser(ShortcutsMixin, ConfigDiffMixin, ExtendedConfigParser): pass


class ConfigDict(UserDict):
    
    def __init__(self, filename):
        self._filename = filename
        if isinstance(filename, dict): return super().__init__(filename)
        try:
            with open(os.path.join(CONFDIR, filename)) as fp:
                return super().__init__(json.load(fp))
        except FileNotFoundError:
            try:
                dct = json.loads(pkgutil.get_data(__name__,"../share/%s"%filename).decode())
                return super().__init__(dct)
            except FileNotFoundError as e: raise #super().__init__()
    
    def __setitem__(self, *args, **xargs):
        super().__setitem__(*args, **xargs)
        self.save()
    
    def save(self):
        with open(os.path.join(CONFDIR, self._filename),"w") as fp:
            json.dump(dict(self), fp)


try: os.mkdir(CONFDIR)
except OSError: pass
default = pkgutil.get_data(__name__,"../share/main.cfg.default").decode()
config = ConfigParser(FILE)
config.read_string(default)
config.read([FILE])

