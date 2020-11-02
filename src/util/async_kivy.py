from threading import Lock


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
    class Previous:
        is_set = False
        value = None
    
    def on_widget_change(*args):
        if lock.locked(): return
        new = widget_getter(*args)
        if not Previous.is_set:
            raise RuntimeError("on_value_change must be called initially.")
        with lock: widget_setter(Previous.value)
        try: value_setter(new)
        except Exception as e: print(repr(e))
    def on_value_change(*args, **xargs):
        with lock:
            widget_setter(value_getter())
            Previous.value = value_getter()
            Previous.is_set = True
        
    return on_value_change, on_widget_change

