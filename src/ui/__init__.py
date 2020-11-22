import gi
gi.require_version("Gtk", "3.0")
gi.require_version('Notify', '0.7')
gi.require_version('AppIndicator3', '0.1')
from gi.repository import GLib, Gtk, Gdk, Notify, AppIndicator3
import sys, pkgutil
from threading import Timer
from ..util.async_widget import bind_widget_to_value
from ..amp import features
from ..config import config
from ..util.function_bind import Bindable
from .. import NAME


Notify.init(NAME)


def gtk(func):
    return lambda *args,**xargs: GLib.idle_add(lambda:func(*args,**xargs))


class _Icon(Bindable):

    def set_icon(self, icon, help):
        """ @icon binary """
        with open(self._icon_path,"wb") as fp: icon.save(fp, "PNG")
        self.set_icon_by_path(self._icon_path, help)
        

class _Notification(Bindable):

    def set_urgency(self, n): pass


class GUI_Backend:

    def mainloop(self): Gtk.main()


class GladeGtk:
    GLADE = ""
    
    def __init__(self, *args, **xargs):
        super().__init__(*args, **xargs)
        if not self.__class__.__dict__.get("_inited", False):
            setattr(self.__class__, "_inited", True)
            self._init_once()

    def _init_once(self):
        cls = self.__class__
        cls.instance = self
        cls.builder = Gtk.Builder()
        cls.builder.add_from_string(pkgutil.get_data(__name__, cls.GLADE).decode())
        cls.builder.connect_signals(self)

    @gtk
    def show(self): self.window.show_all()

    @gtk
    def hide(self): self.window.hide()


class GaugeNotification(GladeGtk, _Notification):
    GLADE = "../share/gauge_notification.glade"
    _timeout = 2
    
    def __init__(self, *args, **xargs):
        super().__init__(*args, **xargs)
        self._position()
        
    def _init_once(self):
        super()._init_once()
        cls = self.__class__
        cls.level = cls.builder.get_object("level")
        cls.title = cls.builder.get_object("title")
        cls.subtitle = cls.builder.get_object("subtitle")
        cls.window = cls.builder.get_object("window")
        cls.width, cls.height = cls.window.get_size()
    
    def set_timeout(self, t): self._timeout = t/1000
    
    def on_click(self, *args): self.hide()
    
    @gtk
    def update(self, title, message, value, min, max):
        assert(min <= value <= max)
        diff = max-min
        value_normalised = (value-min)/diff
        self.title.set_text(title)
        self.subtitle.set_text(message)
        self.level.set_value(value_normalised*100)

    @gtk
    def _position(self):
        self.window.move(self.window.get_screen().get_width()-self.width-50, 170)

    def show(self):
        super().show()
        try: self._timer.cancel()
        except: pass
        self._timer = Timer(self._timeout, self.hide)
        self._timer.start()


class VolumePopup(GladeGtk):
    GLADE = "../share/volume_popup.glade"
    
    def __init__(self, amp, *args, **xargs):
        super().__init__(*args, **xargs)
        self.amp = amp

        self.window = self.builder.get_object("window")
        self.width, self.height = self.window.get_size()
        self.scale = self.builder.get_object("scale")
        self.label = self.builder.get_object("label")
        self.image = self.builder.get_object("image")
        self.adj = self.builder.get_object("adjustment")
        
        f = amp.features["volume"]
        self.adj.set_lower(f.min)
        self.adj.set_upper(f.max)
        self.adj.set_page_increment(config.getdecimal("GUI","tray_scroll_delta"))
        on_value_change, self.on_widget_change = bind_widget_to_value(
            f.get, f.set, self.scale.get_value, self.set_value)
        f.bind(on_change=gtk(on_value_change))
        features.require("volume")(lambda amp:on_value_change())(amp)

    def set_value(self, value):
        self.scale.set_value(value)
        self.label.set_text("%0.1f"%value)
        
    @gtk
    def set_image(self, path):
        self.image.set_from_file(path)
        
    def on_change(self, event): self.on_widget_change()

    def on_focus_out(self, *args): self.hide()
    
    @property
    def visible(self): return self.window.get_visible()


class Notification(_Notification, Notify.Notification):

    def show(self, *args, **xargs):
        try: return super().show(*args,**xargs)
        except GLib.Error as e: print(repr(e), file=sys.stderr)


class Icon(Bindable):
    
    def __init__(self, amp):
        super().__init__()
        self.amp = amp
        self.icon = AppIndicator3.Indicator.new(NAME, NAME, AppIndicator3.IndicatorCategory.HARDWARE)
        self.popup = VolumePopup(amp)
        self.icon.connect("scroll-event", self.on_scroll)
        self.icon.set_menu(self.build_menu())
        
    def on_scroll_up(self, steps): pass
    
    def on_scroll_down(self, steps): pass
    
    def build_menu(self):
        menu = Gtk.Menu()

        item_volume = Gtk.MenuItem('Volume')
        item_volume.connect('activate', lambda event:self.popup.show())
        menu.append(item_volume)

        item_power = Gtk.CheckMenuItem("Power")
        f = self.amp.features["power"]
        self.amp.preload_features.add("power")
        on_value_change, on_widget_change = bind_widget_to_value(
            f.get, f.set, item_power.get_active, item_power.set_active)
        f.bind(on_change=gtk(on_value_change))
        item_power.connect("toggled", lambda event:on_widget_change())
        menu.append(item_power)

        menu.append(Gtk.SeparatorMenuItem())

        item_poweron = Gtk.CheckMenuItem("Auto power on")
        item_poweron.set_active(config.getboolean("Amp","control_power_on"))
        item_poweron.connect("toggled", lambda *args:
            config.setboolean("Amp","control_power_on",item_poweron.get_active()))
        menu.append(item_poweron)

        item_poweroff = Gtk.CheckMenuItem("Auto power off")
        item_poweroff.set_active(config.getboolean("Amp","control_power_off"))
        item_poweroff.connect("toggled", lambda *args:
            config.setboolean("Amp","control_power_off",item_poweroff.get_active()))
        menu.append(item_poweroff)

        menu.append(Gtk.SeparatorMenuItem())

        item_quit = Gtk.MenuItem('Quit')
        item_quit.connect('activate', lambda *args: Gtk.main_quit())
        menu.append(item_quit)

        menu.show_all()
        return menu
            
    def on_scroll(self, icon, steps, direction):
        if direction == Gdk.ScrollDirection.UP: self.on_scroll_up(steps)
        elif direction == Gdk.ScrollDirection.DOWN: self.on_scroll_down(steps)
    
    @gtk
    def show(self): self.icon.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
    
    @gtk
    def hide(self): self.icon.set_status(AppIndicator3.IndicatorStatus.PASSIVE)
    
    @gtk
    def set_icon(self, *args): self.icon.set_icon_full(*args)
    
    def connect(self, *args, **xargs): self.icon.connect(*args,**xargs)


css = b'''
window.dark { background-color: #2e2e2e; }
label.dark { color: #ded6d6; font-weight: bold }
'''
screen = Gdk.Screen.get_default()
css_provider = Gtk.CssProvider()
css_provider.load_from_data(css)
context = Gtk.StyleContext()
context.add_provider_for_screen(screen, css_provider,
                                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)


