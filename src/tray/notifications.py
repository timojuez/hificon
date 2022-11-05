import gi
gi.require_version('Notify', '0.7')
from gi.repository import GLib, Notify
import sys
from threading import Timer
from ..core.util.function_bind import Bindable
from ..core import features
from .common import config, resolve_feature_id, gtk, GladeGtk, APP_NAME, Singleton, TargetApp
from .tray import TrayMixin
from .key_binding import KeyBinding


Notify.init(APP_NAME)


class _Notification(Bindable):

    def set_urgency(self, n): pass


class GaugeNotification(GladeGtk, _Notification, metaclass=Singleton):
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
        if not (min <= value <= max):
            return sys.stderr.write(f"[{self.__class__.__name__}] WARNING: "
                f"Value out of bounds: {value}. title='{title}', message='{message}'.\n")
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


class Notification(_Notification, Notify.Notification):
    _button_clicked = False

    def __init__(self, timeout_action=None, default_click_action=None, buttons=None, *args, **xargs):
        super().__init__(*args, **xargs)
        if buttons:
            for name, func in buttons:
                self.add_action(name, name,
                    lambda *args,func=func,**xargs: [func(), setattr(self, '_button_clicked', True)])
        self.connect("closed", self.on_popup_closed)
        self._timeout_action = timeout_action
        self._default_click_action = default_click_action

    def on_popup_closed(self, *args):
        if self.get_closed_reason() == 1: # timeout
            if self._timeout_action: self._timeout_action()
        elif self.get_closed_reason() == 2 and not self._button_clicked: # clicked outside buttons
            if self._default_click_action: self._default_click_action()
        self._button_clicked = False
    
    def show(self, *args, **xargs):
        try: return super().show(*args,**xargs)
        except GLib.Error as e: print(repr(e), file=sys.stderr)

    def close(self, *args, **xargs):
        try: super().close(*args, **xargs)
        except: pass


class FeatureNotification:

    def __init__(self, feature, *args, **xargs):
        super().__init__(*args, **xargs)
        self.f = feature
        self.target = feature.target


class TextNotification(FeatureNotification, Notification):
    
    def __init__(self, *args, **xargs):
        super().__init__(*args, **xargs)
        self.set_urgency(2)
        self.set_timeout(config["notifications"]["timeout"])
        super().update("Connecting ...", self.target.uri)
        self.target.preload_features.add("name")
    
    def update(self): self.target.schedule(self._update, requires=("name",))
    
    def _update(self, name):
        if not self.f.isset(): return
        val = {True:"On",False:"Off"}.get(self.f.get(), self.f.get())
        super().update(f"{self.f.name}: {val}", name.get())

    def show(self): self.target.schedule(lambda _: super(TextNotification, self).show(), requires=("name",))


class NumericNotification(FeatureNotification):
    
    def __init__(self, scale_popup, *args, **xargs):
        super().__init__(*args, **xargs)
        self.scale_popup = scale_popup
        self._n = GaugeNotification()
        self._n.set_timeout(config["notifications"]["timeout"])

    def update(self): pass

    def show(self):
        if self.scale_popup._current_feature == self.f and self.scale_popup.visible: return
        self._n.update(
            title=self.f.name,
            message=str(self.f),
            value=self.f.get() if self.f.isset() else self.f.min,
            min=self.f.min,
            max=self.f.max)
        self._n.show()

    def hide(self): self._n.hide()


class NotificationMixin(TrayMixin, KeyBinding, TargetApp):
    """ Does the graphical notifications """

    def __init__(self, *args, **xargs):
        super().__init__(*args, **xargs)
        self._notifications = {f.id: self.create_notification(f) for f in self.target.features.values()}
        self.target.bind(on_feature_change = self.show_notification_on_feature_change)
    
    def create_notification(self, f):
        if isinstance(f, features.NumericFeature): return NumericNotification(self.scale_popup, f)
        if isinstance(f, features.SelectFeature): return TextNotification(f,
            buttons=[("Don't show again", lambda: self.settings.notification_blacklist.add_item(f.id))])

    def show_notification(self, f_id):
        if f_id not in [resolve_feature_id(f_id) for f_id in config["notifications"]["blacklist"]]:
            if n := self._notifications.get(f_id): n.show()

    def on_mouse_down(self,*args,**xargs):
        self.show_notification(config.gesture_feature)
        super().on_mouse_down(*args,**xargs)

    def on_volume_key_press(self,*args,**xargs):
        self.show_notification(config.hotkeys_feature)
        super().on_volume_key_press(*args,**xargs)

    def show_notification_on_feature_change(self, f_id, value): # bound to target
        if n := self._notifications.get(f_id): n.update()
        if self.target.features[f_id]._prev_val is not None: self.show_notification(f_id)

    def on_scroll_up(self, *args, **xargs):
        self.show_notification(config.tray_feature)
        super().on_scroll_up(*args,**xargs)
        
    def on_scroll_down(self, *args, **xargs):
        self.show_notification(config.tray_feature)
        super().on_scroll_down(*args,**xargs)

