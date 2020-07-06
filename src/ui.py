import tempfile
from .util.function_bind import Bindable


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


class _Notification(Bindable): pass


def loadwx():
    # use wxwidgets
    global backend, init, mainloop, Icon, Notification
    backend = "wx"
    
    import wx
    from wx.adv import NotificationMessage, TaskBarIcon


    def init(name):
        global app
        app = wx.App()
    
    def mainloop(): app.MainLoop()
    

    class Notification(_Notification, NotificationMessage):
        
        def update(self, title=None, message=None):
            if message: wx.CallAfter(self.SetMessage,message)
            if title: wx.CallAfter(self.SetTitle,title)
        
        def set_urgency(self, n): pass
        
        def set_timeout(self, t): self._timeout = t/1000
        
        def show(self): wx.CallAfter(self.Show, timeout=self._timeout)

    
    class Icon(_Icon, TaskBarIcon):
        
        def show(self): wx.CallAfter(self.SetIcon, *self._seticon)
        
        def hide(self): wx.CallAFter(self.RemoveIcon)
        
        def set_icon_by_path(self, path, help):
            self._seticon = (wx.Icon(path), help)
            self.show()
        
        def connect(self, *args, **xargs): pass
        

    return dict(init=init, mainloop=mainloop, Notification=Notification, Icon=Icon, backend="wx")
    
    
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


    class Notification(_Notification, Notify.Notification): pass


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
        
        
