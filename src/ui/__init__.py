import wx, tempfile, os, sys
from threading import Timer
from ..util.function_bind import Bindable
from . import gauge_notification


def CallAfter(func):
    def decorator(*args, **xargs):
        wx.CallAfter(func, *args, **xargs)
    return decorator
    

class _Icon(Bindable):

    def __init__(self, *args, **xargs):
        self._icon_path = tempfile.mktemp()
        super().__init__(*args,**xargs)
            
    def set_icon(self, icon, help):
        """ @icon binary """
        with open(self._icon_path,"wb") as fp: icon.save(fp, "PNG")
        self.set_icon_by_path(self._icon_path, help)
        
    def __del__(self):
        try: os.remove(self._icon_path)
        except: pass
        
    def on_scroll_up(self, steps): pass
    
    def on_scroll_down(self, steps): pass


class _Notification(Bindable):

    def set_urgency(self, n): pass


class GaugeNotification(_Notification, gauge_notification.GaugeNotification): 
    _timeout = 2
    _min = 0
    _max = 100
    _value = 0
    _title = ""
    _message = ""
    
    def __init__(self):
        frame = gauge_notification.Frame(None)
        super().__init__(frame)
    
    def set_timeout(self, t): self._timeout = t/1000
    
    def on_click(self, *args): self.hide()
    
    @CallAfter
    def update(self, title=None, message=None, value=None, min=None, max=None):
        if not message and value is not None: message = "%0.1f"%value
        if title is not None: self._title = title
        if message is not None: self._message = message
        if value is not None: self._value = value
        if min is not None: self._min = min
        if max is not None: self._max = max

        self.title.SetLabel(self._title)
        self.subtitle.SetLabel(self._message)
        totalheight = self.empty.Size.GetHeight()+self.progress.Size.GetHeight()
        progressheight = int((self._value-self._min)/(self._max-self._min)*totalheight)
        self.progress.SetSize(self.progress.Size.GetWidth(), progressheight)
        self.progress.SetSizeHints(self.progress.Size.GetWidth(),progressheight)
        self.empty.SetSizeHints(self.empty.Size.GetWidth(), totalheight-self.progress.Size.GetHeight())
        self.GetSizer().Layout()

    @CallAfter
    def show(self):
        self.GetParent().SetPosition((wx.DisplaySize()[0]-self.GetParent().Size.GetWidth()-20, 170))
        self.GetParent().Show(True)
        try: self._timer.cancel()
        except: pass
        self._timer = Timer(self._timeout, self.hide)
        self._timer.start()

    @CallAfter
    def hide(self): self.GetParent().Hide()
    

def loadwx():
    # use wxwidgets
    global backend, init, mainloop, Icon, Notification
    backend = "wx"
    
    from wx.adv import NotificationMessage, TaskBarIcon


    def init(name):
        global app
        app = wx.App()
    
    def mainloop(): app.MainLoop()
    

    class Notification(_Notification, NotificationMessage):
        
        _timeout = NotificationMessage.Timeout_Auto
        
        @CallAfter
        def update(self, title=None, message=None):
            if message: self.SetMessage(message)
            if title: self.SetTitle(title)
        
        def set_urgency(self, n): pass
        
        def set_timeout(self, t): self._timeout = t/1000
        
        @CallAfter
        def show(self): self.Show(timeout=self._timeout)

        @CallAfter
        def close(self): self.Close()

    
    class Icon(_Icon, TaskBarIcon):
        
        @CallAfter
        def show(self): self.SetIcon(*self._seticon)
        
        @CallAfter
        def hide(self): self.RemoveIcon()
        
        def set_icon_by_path(self, path, help):
            self._seticon = (wx.Icon(path), help)
            self.show()
        
        def connect(self, *args, **xargs): pass
        
    
def loadgtk():
    # use Gtk
    global backend, init, mainloop, Icon, Notification
    backend = "gtk"
    
    import gi
    gi.require_version('Gtk', '3.0')
    gi.require_version('Notify', '0.7')
    gi.require_version('AppIndicator3', '0.1')
    from gi.repository import GLib, Gtk, Gdk, Notify, AppIndicator3


    def init(name):
        global _name
        _name = name
        Notify.init(name)
    
    def mainloop():
        if not GLib.MainLoop().is_running(): GLib.MainLoop().run()


    class Notification(_Notification, Notify.Notification):

        def show(self, *args, **xargs):
            try: return super().show(*args,**xargs)
            except GLib.Error as e: print(repr(e), file=sys.stderr)

        def add_action(self, title, callback): super().add_action("action", title, callback)


    class Icon(_Icon):
        
        def __init__(self):
            super().__init__()
            self.icon = AppIndicator3.Indicator.new(_name, _name, AppIndicator3.IndicatorCategory.HARDWARE)
            self.icon.connect("scroll-event", self.on_scroll)
            
        def on_scroll(self, icon, steps, direction):
            if direction == Gdk.ScrollDirection.UP: self.on_scroll_up(steps)
            elif direction == Gdk.ScrollDirection.DOWN: self.on_scroll_down(steps)
            
        def show(self): GLib.idle_add(lambda:self.icon.set_status(AppIndicator3.IndicatorStatus.ACTIVE))
        
        def hide(self): GLib.idle_add(lambda:self.icon.set_status(AppIndicator3.IndicatorStatus.PASSIVE))
        
        def set_icon_by_path(self, path, help): GLib.idle_add(lambda:self.icon.set_icon_full(path, help))
        
        def connect(self, *args, **xargs): self.icon.connect(*args,**xargs)
        
        
