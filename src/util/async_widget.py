from threading import Lock
import traceback, sys


def bind_widget_to_value(value_getter, value_setter, widget_getter, widget_setter):
    """
    Binds a widget with given getter and setter asynchronously to a value so that 
        the widget always stays synchronised with the value.
        You must call on_value_change once before you bind on_widget_change to the widget.
    Returns the functions that shall be called when the value resp. widget changes
    @value_getter: callable
    @value_setter: callable(new value)
    @widget_getter: callable
    @widget_setter: callable(new value)
    @returns: (callable on_value_change, callable on_widget_change)
        on_value_change(*a) will call get_from_widget(*a)
    """
    lock = Lock()

    class Actual:
        is_set = False
        value = None
    
    def on_widget_change(*args):
        if not Actual.is_set:
            raise RuntimeError("on_value_change must be called initially.")
        if lock.locked() and Actual.value == widget_getter(*args): return # Kivy workaround
        with lock:
            candidate_value = widget_getter(*args)
            if candidate_value == Actual.value: return # skip calls caused by widget_setter
        widget_setter(Actual.value)
        try: value_setter(candidate_value)
        except: print(traceback.format_exc(), file=sys.stderr)

    def on_value_change(*args, **xargs):
        with lock:
            Actual.value = value_getter()
            Actual.is_set = True
            widget_setter(value_getter())
        
    return on_value_change, on_widget_change

