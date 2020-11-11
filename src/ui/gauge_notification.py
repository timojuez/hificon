import argparse, os, pkgutil

os.environ["KIVY_NO_ARGS"] = "1"
from kivy.config import Config

Config.set('graphics', 'borderless', True)
Config.set('graphics', 'resizable', False)
Config.set('graphics', 'window_state', 'hidden')
Config.set('graphics', 'width', 101)
Config.set('graphics', 'height', 234)

from kivy.app import App
from kivy.lang import Builder
from kivy.core.window import Window
from kivy.uix.gridlayout import GridLayout
from kivy.uix.stacklayout import StackLayout
from kivy.uix.boxlayout import BoxLayout


class GaugeNotification(BoxLayout):
    _timeout = 2
    _min = 0
    _max = 100
    _value = 0
    _title = ""
    _message = ""
    
    def set_timeout(self, t): self._timeout = t/1000
    
    def on_click(self, *args): self.hide()
    
    def myupdate(self, title=None, message=None, value=None, min=None, max=None):
        if not message and value is not None: message = "%0.1f"%value
        if title is not None: self._title = title
        if message is not None: self._message = message
        if value is not None: self._value = value
        if min is not None: self._min = min
        if max is not None: self._max = max

        self.ids.title.text = str(title)
        self.ids.subtitle.text = str(self._message)
        self.ids.bottom.size_hint_y = float((self._value-self._min)/(self._max-self._min))
    
    def show(self):
        Window.show()
        #Window.left = wx.DisplaySize()[0]-self.GetParent().Size.GetWidth()-20
        Window.left = 1800
        try: self._timer.cancel()
        except: pass
        self._timer = Timer(self._timeout, self.hide)
        self._timer.start()

    def hide(self): Window.hide()


class _App(App):

    def build(self):
        return GaugeNotification()


kv = pkgutil.get_data(__name__,"../share/gauge_notification.kv").decode()
if __name__ == '__main__':
    Builder.load_string(kv)
    Window.top = 170
    _App().run()

