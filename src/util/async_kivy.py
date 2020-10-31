from threading import Lock


def bind_widget_to_value(value_getter, value_setter, widget_getter, widget_setter):
    """
    Binds a widget with given getter and setter asynchronously to a value so that 
        the widget always stays synchronised with the value.
    Returns the functions that shall be called when the value resp. widget changes
    @value_getter: callable
    @value_setter: callable(new value)
    @widget_getter: callable
    @widget_setter: callable(new value)
    @returns: (callable on_variable_change, callable on_widget_change)
        on_value_change(*a) will call get_from_widget(*a)
    """
    lock = Lock()
    def update_widget(*args,**xargs):
        with lock: widget_setter(value_getter())
    
    def on_widget_change(*args):
        if lock.locked(): return
        new = widget_getter(*args)
        update_widget()
        try: value_setter(new)
        except Exception as e: print(repr(e))
    return update_widget, on_widget_change

