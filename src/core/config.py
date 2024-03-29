# -*- coding: utf-8 -*- 

import os, configparser, pkgutil, json, yaml
from collections import UserDict
from decimal import Decimal
from copy import deepcopy
from ..info import PKG_NAME


CONFDIR = os.path.expanduser("~/.%s"%PKG_NAME)
FILE = os.path.join(CONFDIR, "main.cfg")


def decimal_constructor(loader, node):
    value = loader.construct_scalar(node)
    return Decimal(value)

def decimal_representer(dumper, data):
    return dumper.represent_scalar(u'!decimal', str(data))

yaml.add_representer(Decimal, decimal_representer)
yaml.add_constructor('!decimal', decimal_constructor)


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


class ConfigParser(ConfigDiffMixin, ExtendedConfigParser): pass


class _Config(UserDict):
    
    def __init__(self, filename):
        self._filename = filename
        if isinstance(filename, dict): return super().__init__(filename)
        dct = self.str_to_dict(pkgutil.get_data(__name__,"../share/%s.default"%filename).decode())
        try:
            with open(os.path.join(CONFDIR, filename)) as fp:
                user = self.str_to_dict(fp.read())
        except FileNotFoundError: pass
        else: dct = dict(deep_merge(dct, user))
        super().__init__(dct)

    def __setitem__(self, *args, **xargs):
        super().__setitem__(*args, **xargs)
        self.save()
    
    def save(self):
        with open(os.path.join(CONFDIR, self._filename),"w") as fp:
            fp.write(self.dict_to_str(dict(self)))

    def str_to_dict(self, s): raise NotImplementedError()
    def dict_to_str(self, d): raise NotImplementedError()

    def connect_to_object(self, config_property, getter, setter):
        """
        Synchronises a config property to another object
        config_property: path to value under config as tuple. Is ("item") for config["item"]
        getter and setter refer to the external object.
        returns a function that has to be called whenever the object's value changes
        """
        config_property = list(config_property)
        item = config_property.pop()
        path = self
        for p in config_property: path = path[p]
        setter(path[item])
        def on_changed(*args, **xargs):
            path[item] = getter()
            self.save()
        return on_changed


def deep_merge(dict1, dict2):
    overlapping_keys = dict1.keys() & dict2.keys()
    for key in overlapping_keys:
        if isinstance(dict1[key], dict) and isinstance(dict2[key], dict):
            yield key, dict(deep_merge(dict1[key], dict2[key]))
        else:
            yield key, deepcopy(dict2[key])
    for key in dict1.keys() - overlapping_keys:
        yield key, deepcopy(dict1[key])
    for key in dict2.keys() - overlapping_keys:
        yield key, deepcopy(dict2[key])


class DictConfig(_Config):

    def str_to_dict(self, s): return json.loads(s)
    def dict_to_str(self, d): return json.dumps(d)


class YamlConfig(_Config):

    def str_to_dict(self, s): return yaml.full_load(s)
    def dict_to_str(self, d): return yaml.dump(d)


try: os.mkdir(CONFDIR)
except OSError: pass
default = pkgutil.get_data(__name__,"../share/main.cfg.default").decode()
config = ConfigParser(FILE)
config.read_string(default)
config.read([FILE])

