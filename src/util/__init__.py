import sys
from .call_sequence import *
from .function_bind import *


def log_call(func):
    """ object function decorator """
    def call(self,*args,**xargs):
        try: assert(not (self.verbose > 3))
        except:
            print("[%s] %s"%(self.__class__.__name__, func.__name__), file=sys.stderr)
        return func(self,*args,**xargs)
    return call

