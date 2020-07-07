import wx, tempfile, os
from threading import Timer
from .util.function_bind import Bindable


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


class GaugeNotification(_Notification, wx.Frame): 
    _timeout = 2
    _min = 0
    _max = 100
    _value = 0
    _title = ""
    _message = ""
    
    def __init__(self, parent=None, title="GaugeNotification"):
        super().__init__(parent, title = title,style=wx.STAY_ON_TOP|wx.FRAME_NO_TASKBAR|wx.BORDER_NONE)
        screen_width, screen_height = wx.DisplaySize()

        self.width = screen_width*0.045
        self.height = screen_height*.3
        self.dim = (screen_width-self.width-screen_width*0.01, screen_height*0.1)
        self.bar_width = self.width*.2
        self.bar_height = self.height*0.7

        background = wx.SystemSettings.GetColour(wx.SYS_COLOUR_MENUBAR)
        text = wx.SystemSettings.GetColour(wx.SYS_COLOUR_CAPTIONTEXT)
        self.bar1 = wx.SystemSettings.GetColour(wx.SYS_COLOUR_MENUHILIGHT)
        self.bar2 = wx.SystemSettings.GetColour(wx.SYS_COLOUR_CAPTIONTEXT)
        
        self.pnl = wx.Panel(self) 
        self.pnl.SetBackgroundColour(background)
        self.pnl.SetForegroundColour(text)
        self.border = wx.BoxSizer(wx.VERTICAL)
        vbox_outer = wx.BoxSizer(wx.VERTICAL)
        self.vbox_inner = wx.BoxSizer(wx.VERTICAL)
		    
        self.text1 = wx.StaticText(self.pnl)
        self.text2 = wx.StaticText(self.pnl)
        
        vbox_outer.Add(self.text1, border=5, flag=wx.ALL|wx.ALIGN_CENTER)
        vbox_outer.Add(self.vbox_inner, proportion=1, flag=wx.ALIGN_CENTER)
        vbox_outer.Add(self.text2, border=5, flag=wx.ALL|wx.ALIGN_CENTER)
        self.border.Add(vbox_outer, border=10, flag=wx.ALL|wx.EXPAND)
        self.pnl.SetSizer(self.border)

        self.SetSize((self.width, self.height))
        self.SetPosition(self.dim)

    def set_timeout(self, t): self._timeout = t/1000
    
    @CallAfter
    def update(self, title=None, message=None, value=None, min=None, max=None):
        if not title and value is not None: title = "%0.1f"%value
        if title is not None: self._title = title
        if message is not None: self._message = message
        if value is not None: self._value = value
        if min is not None: self._min = min
        if max is not None: self._max = max

        self.text2.SetLabel(self._message)
        self.vbox_inner.Clear()
        buttomHeight = int((self._value-self._min)/(self._max-self._min)*self.bar_height)
        self.top = wx.Window(self.pnl,size=(self.bar_width,self.bar_height-buttomHeight))
        self.top.SetBackgroundColour(self.bar2)
        self.buttom = wx.Window(self.pnl, size=(self.bar_width,buttomHeight))
        self.buttom.SetBackgroundColour(self.bar1)
        self.vbox_inner.Add(self.top)
        self.vbox_inner.Add(self.buttom)
        self.text1.SetLabel(self._title)
        self.Update()

    @CallAfter
    def show(self):
        self.Show(True)
        try: self._timer.cancel()
        except: pass
        self._timer = Timer(self._timeout, self.hide)
        self._timer.start()

    @CallAfter
    def hide(self): self.Hide()
    

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
        
        _timeout = NotificationMessage.Timeout_Auto
        
        @CallAfter
        def update(self, title=None, message=None):
            if message: self.SetMessage(message)
            if title: self.SetTitle(title)
        
        def set_urgency(self, n): pass
        
        def set_timeout(self, t): self._timeout = t/1000
        
        @CallAfter
        def show(self): self.Show(timeout=self._timeout)

    
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
        
        
