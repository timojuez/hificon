import importlib


def getProtocols():
    """
    returns a list in the format [(name, module)]
    """
    def getModule(name):
        try:
            module = importlib.import_module(".%s"%name, __name__)
            return module.Amp.protocol, module
        except Exception as e: print(repr(e))
        
    protocols = ["denon","emulator","raw_telnet","auto"]
    return list(filter(lambda e:e, [getModule(mname) for mname in protocols]))

