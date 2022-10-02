import gi
gi.require_version("Gtk", "3.0")
gi.require_version('Notify', '0.7')
gi.require_version('AppIndicator3', '0.1')
from gi.repository import GLib, Gtk, Gdk, Notify, AppIndicator3, GdkPixbuf, Gio
import sys, pkgutil
from threading import Timer
from ..core.util.async_widget import bind_widget_to_value
from ..core import features, config
from ..core.util.function_bind import Bindable
from ..info import NAME, AUTHOR, URL, VERSION, COPYRIGHT
from .common import gtk, GladeGtk
from .settings import Settings


Notify.init(NAME)


class _Icon(Bindable):

    def set_icon(self, icon, help):
        """ @icon binary """
        with open(self._icon_path,"wb") as fp: icon.save(fp, "PNG")
        self.set_icon_by_path(self._icon_path, help)
        

class _Notification(Bindable):

    def set_urgency(self, n): pass


class GUI_Backend:

    def mainloop(self): Gtk.main()
    
    @classmethod
    def exit(self): Gtk.main_quit()



class GaugeNotification(GladeGtk, _Notification):
    GLADE = "../share/gauge_notification.glade"
    _timeout = 2
    
    def __init__(self, *args, **xargs):
        super().__init__(*args, **xargs)
        self._position()
        self.level = self.builder.get_object("level")
        self.title = self.builder.get_object("title")
        self.subtitle = self.builder.get_object("subtitle")
        self.window = self.builder.get_object("window")
        self.width, self.height = self.window.get_size()
    
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


class HideOnUnfocusMixin:
    """ Adds a popup behaviour to a window object: It closes, when the user clicks outside of it """

    def __init__(self, *args, **xargs):
        super().__init__(*args, **xargs)
        self.window = self.builder.get_object("window")
        self.window.set_keep_above(True)
        self.window.connect("map-event", self.pointer_grab)
        self.window.connect("unmap-event", self.pointer_ungrab)
        self.window.connect("button-press-event", self. on_button_press)

    def on_button_press(self, widget, event):
        p_x, p_y = self.window.get_pointer()
        w_x, w_y = self.window.get_size()
        if p_x < 0 or p_y < 0 or p_x > w_x or p_y > w_y: # pointer outside window
            self.hide()

    def pointer_grab(self, *args):
        Gdk.pointer_grab(self.window.get_window(), True, Gdk.EventMask.BUTTON_PRESS_MASK, None, None, 0)

    def pointer_ungrab(self, *args): Gdk.pointer_ungrab(0)


class ScalePopup(HideOnUnfocusMixin, GladeGtk):
    GLADE = "../share/scale_popup.glade"
    
    def __init__(self, target, *args, **xargs):
        super().__init__(*args, **xargs)
        self.target = target
        self._current_feature = None

        self.window = self.builder.get_object("window")
        self.width, self.height = self.window.get_size()
        self.scale = self.builder.get_object("scale")
        self.label = self.builder.get_object("label")
        self.title = self.builder.get_object("title")
        self.image = self.builder.get_object("image")
        self.adj = self.builder.get_object("adjustment")
        self.adj.set_page_increment(config.getdecimal("Tray","tray_scroll_delta"))
        
        for f in self.target.features.values(): f.bind(
            gtk(lambda *args, f=f, **xargs: f==self._current_feature and self.on_value_change(*args,**xargs)))

    def set_value(self, value):
        self.scale.set_value(value)
        self.label.set_text(str(self._current_feature))
        
    @gtk
    def set_image(self, path):
        self.image.set_from_file(path)
        
    def on_change(self, event): self.on_widget_change()
    
    @property
    def visible(self): return self.window.get_visible()
    
    @gtk
    def show(self, f):
        self.on_value_change, self.on_widget_change = bind_widget_to_value(
            f.get, f.remote_set, self.scale.get_value,
            lambda value: f==self._current_feature and self.set_value(value))
        self.title.set_text(f.name)
        self.adj.set_lower(f.min)
        self.adj.set_upper(f.max)
        self._current_feature = f
        self.on_value_change()
        super().show()


class Notification(_Notification, Notify.Notification):

    def show(self, *args, **xargs):
        try: return super().show(*args,**xargs)
        except GLib.Error as e: print(repr(e), file=sys.stderr)


class MenuMixin:
    _header_items = {}
    _footer_items = []

    def __init__(self, *args, **xargs):
        super().__init__(*args, **xargs)
        self._menu = Gtk.Menu()

        # header features
        for f in self.target.features.values():
            try: item = self.add_feature(f, True)
            except TypeError: pass
            else: self._header_items[f] = item

        item_disconnected = Gtk.MenuItem("Connecting ...", sensitive=False)
        self._footer_items.append(item_disconnected)
        self.target.bind(on_connect = gtk(item_disconnected.hide))
        self.target.bind(on_disconnected = gtk(item_disconnected.show))

        item_more = Gtk.MenuItem("All Settings", no_show_all=True)
        self.target.bind(on_connect = gtk(item_more.show))
        self.target.bind(on_disconnected = gtk(item_more.hide))
        submenu = Gtk.Menu()
        categories = {cat: {"menu":Gtk.Menu(), "item":Gtk.MenuItem(cat, no_show_all=True)}
            for cat in self.target.feature_categories}
        for d in categories.values():
            submenu.append(d["item"])
            d["item"].set_submenu(d["menu"])
            self.target.bind(on_disconnected=gtk(lambda i=d["item"]: i.hide()))
        for key, f in self.target.features.items():
            d = categories[f.category]
            try: d["menu"].append(self.add_feature(f, False))
            except TypeError: pass
            else: f.bind(on_set = gtk(lambda i=d["item"]: i.show()))
        def poll_all():
            try:
                for f in self.target.features.values(): f.async_poll()
            except ConnectionError: pass
        self.target.bind(on_connect=lambda:Timer(1, poll_all).start())
        item_more.set_submenu(submenu)
        self._footer_items.append(item_more)

        self._footer_items.append(Gtk.SeparatorMenuItem())

        item_poweron = Gtk.CheckMenuItem("Auto power on")
        item_poweron.set_active(self.config["auto_power_on"])
        item_poweron.connect("toggled", lambda *args:
            self.config.__setitem__("auto_power_on",item_poweron.get_active()))
        self._footer_items.append(item_poweron)

        item_poweroff = Gtk.CheckMenuItem("Auto power off")
        item_poweroff.set_active(self.config["auto_power_off"])
        item_poweroff.connect("toggled", lambda *args:
            self.config.__setitem__("auto_power_off",item_poweroff.get_active()))
        self._footer_items.append(item_poweroff)

        self._footer_items.append(Gtk.SeparatorMenuItem())

        item_settings = Gtk.MenuItem('Program Settings')
        item_settings.connect('activate', lambda *args: Settings().show())
        self._footer_items.append(item_settings)

        item_about = Gtk.MenuItem('About %s'%NAME)
        item_about.connect('activate', lambda *args: self.build_about_dialog())
        self._footer_items.append(item_about)

        item_quit = Gtk.MenuItem('Quit')
        item_quit.connect('activate', lambda *args: (self.target.exit(), GUI_Backend.exit()))
        self._footer_items.append(item_quit)

        for e in self._footer_items+list(self._header_items.values()): e.show_all()

    def on_menu_settings_change(self, features): self._refill_menu(features)

    @gtk
    def _refill_menu(self, header_features):
        for child in self._menu.get_children(): self._menu.remove(child)
        for f in header_features: self.target.preload_features.add(f.id)
        for f in header_features:
            if item := self._header_items.get(f, None): self._menu.append(item)
        for item in self._footer_items: self._menu.append(item)

    def add_feature(self, f, compact=True):
        """ compact: If true, SelectFeatures show the value in the label.
        and BoolFeatures are Checkboxes without submenus. """
        if isinstance(f, features.BoolFeature): item = self._add_bool_feature(f, compact)
        elif isinstance(f, features.NumericFeature): item = self._add_numeric_feature(f, compact)
        elif isinstance(f, features.SelectFeature): item = self._add_select_feature(f, compact)
        else: raise TypeError(f"Unsupported feature type for {f.id}: {f.type}")
        item.set_no_show_all(True)
        f.bind(on_set = gtk(item.show))
        f.bind(on_unset = gtk(item.hide))
        return item

    def _add_bool_feature(self, f, compact):
        if not compact: return self._add_select_feature(f, compact)
        item = Gtk.CheckMenuItem(f.name)
        on_value_change, on_widget_change = bind_widget_to_value(
            f.get, f.remote_set, item.get_active, item.set_active)
        f.bind(gtk(on_value_change))
        item.connect("toggled", lambda event:on_widget_change())
        return item

    def _add_numeric_feature(self, f, compact):
        item = Gtk.MenuItem(f.name)
        def set(value): item.set_label(f"{f.name}   {f}")
        f.bind(gtk(set))
        item.connect("activate", lambda event:self.scale_popup.show(f))
        return item

    def _add_select_feature(self, f, compact):
        submenu = Gtk.Menu()
        item = Gtk.MenuItem(f.name, submenu=submenu)
        if compact: f.bind(gtk(item.set_label))
        f.bind(gtk(lambda _:self._refill_submenu(f, submenu, compact)))
        return item

    def _refill_submenu(self, f, submenu, compact):
        submenu.foreach(lambda child: child.destroy())
        if compact:
            submenu.append(Gtk.MenuItem(f.name, sensitive=False))
            submenu.append(Gtk.SeparatorMenuItem())
        f_get = f.get()
        if f_get not in f.options:
            submenu.append(Gtk.CheckMenuItem(f_get, sensitive=False, active=True, draw_as_radio=True))
        for o in f.options:
            active = f_get==o
            label = {True: "On", False: "Off"}.get(o, o)
            item = Gtk.CheckMenuItem(label, active=active, draw_as_radio=True)
            def on_activate(item, o=o, active=active):
                if item.get_active() != active:
                    item.set_active(active)
                    f.remote_set(o)
            item.connect("activate", on_activate)
            submenu.append(item)
        submenu.show_all()
    

class Tray(MenuMixin):
    
    def __init__(self, *args, **xargs):
        super().__init__(*args, **xargs)
        Settings(self.target, self.config, on_menu_settings_change=self.on_menu_settings_change)
        self.icon = AppIndicator3.Indicator.new(NAME, NAME, AppIndicator3.IndicatorCategory.HARDWARE)
        self.scale_popup = ScalePopup(self.target)
        self.icon.connect("scroll-event", self.on_scroll)
        self.icon.set_menu(self._menu)
        
    def on_scroll_up(self, steps): pass
    
    def on_scroll_down(self, steps): pass
    
    def build_about_dialog(self):
        ad = Gtk.AboutDialog()
        ad.set_program_name(f"{NAME} Tray Control")
        ad.set_version(VERSION)
        logo = pkgutil.get_data(__name__, "../share/icons/scalable/logo.svg")
        pixbuf = GdkPixbuf.Pixbuf.new_from_stream(Gio.MemoryInputStream.new_from_bytes(GLib.Bytes.new(logo)), None)
        ad.set_logo(pixbuf)
        ad.set_copyright(COPYRIGHT)
        ad.set_website(URL)
        ad.connect("response", lambda *args: ad.destroy())
        ad.show()
        return ad
        
    def on_scroll(self, icon, steps, direction):
        if direction == Gdk.ScrollDirection.UP: self.on_scroll_up(steps)
        elif direction == Gdk.ScrollDirection.DOWN: self.on_scroll_down(steps)
    
    @gtk
    def show(self): self.icon.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
    
    @gtk
    def hide(self): self.icon.set_status(AppIndicator3.IndicatorStatus.PASSIVE)
    
    @gtk
    def set_icon(self, *args): self.icon.set_icon_full(*args)
    

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


