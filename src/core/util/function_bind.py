"""
Example:
    class A(Bindable):
        def on_event(): print(1)
    
    class B(Autobind):
        def on_event(): print(2)
        
    a = A()
    B(a)
    a.on_event() # output: 1\n2
"""

from .call_sequence import *


class Bindable(object):

    def bind(self, **callbacks):
        """
        bind(event=function)
        Register callback on @event. Event can be any function in Amp
        """
        for name, callback in callbacks.items():
            setattr(self, name, call_sequence(getattr(self,name), callback))


class Autobind(object):
    """ Classes that inherit from this class will automatically have their functions bound
    to @obj. For all functions @obj.f, self.f will be called if it exists each time
    after @obj.f is being called. """

    def __new__(cls, obj, *args, **xargs):
        if not isinstance(obj,Bindable): raise ValueError("obj %s must be of type Bindable"%obj)
        events = filter((lambda attr:attr.startswith("on_")), dir(obj))
        dct = {attr: lambda *args,**xargs:None for attr in events}
        cls_events = type("Events_%s"%cls.__name__, (object,), dct)
        cls_complete = type(cls.__name__,(cls,cls_events),{})
        return super().__new__(cls_complete)
        
    def __init__(self, obj, *args, **xargs):
        events = filter((lambda attr:attr.startswith("on_")), dir(obj))
        for attr in events: obj.bind(**{attr:getattr(self,attr)})
        super().__init__(*args,**xargs)

