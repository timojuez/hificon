import gi
gi.require_version("Gtk", "3.0")
gi.require_version('Gtk', '3.0')
gi.require_version('Notify', '0.7')
gi.require_version('AppIndicator3', '0.1')
from gi.repository import GLib, Gtk, Gdk, Notify, AppIndicator3
import tempfile, os, sys, pkgutil
from threading import Timer, Thread
from ..util.async_kivy import bind_widget_to_value
from ..amp import features
from ..config import config
from ..util.function_bind import Bindable
from .. import Amp, NAME


def init(name):
    global _name
    _name = name
    Notify.init(name)


def gtk(func):
    return lambda *args,**xargs: GLib.idle_add(lambda:func(*args,**xargs))


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


class GUI_Backend:
    def mainloop(self): Gtk.main()


class GaugeNotification(_Notification):
    _timeout = 2
    _min = 0
    _max = 100
    _value = 0
    _title = ""
    _message = ""
    
    def __init__(self, *args, **xargs):
        super().__init__(*args, **xargs)
        self._position()
        
    def set_timeout(self, t): self._timeout = t/1000
    
    def on_click(self, *args): self.hide()
    
    @gtk
    def update(self, title=None, message=None, value=None, min=None, max=None):
        try: self._timer.cancel()
        except: pass
        self._timer = Timer(self._timeout, self.hide)
        self._timer.start()

        l_title.set_text(title)
        l_subtitle.set_text(message)
        level.set_min_value(min)
        level.set_max_value(max)
        level.set_value(value)

    @gtk
    def _position(self):
        gauge_window.move(gauge_window.get_screen().get_width()-gauge_width-50, 170)

    @gtk
    def show(self): gauge_window.show_all()

    @gtk
    def hide(self): gauge_window.hide()


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
    

builder = Gtk.Builder()
glade = pkgutil.get_data(__name__,"../share/gauge_notification.glade").decode()
builder.add_from_string(glade)
builder.connect_signals(GaugeNotification())

css = b'''
window { background-color: #2e2e2e; }
label { color: #ded6d6; font-weight: bold }
'''
css_provider = Gtk.CssProvider()
css_provider.load_from_data(css)
context = Gtk.StyleContext()
screen = Gdk.Screen.get_default()
context.add_provider_for_screen(screen, css_provider,
                                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

level = builder.get_object("level")
l_title = builder.get_object("title")
l_subtitle = builder.get_object("subtitle")
gauge_window = builder.get_object("window")
gauge_width, gauge_height = gauge_window.get_size()

