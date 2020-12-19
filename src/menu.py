import argparse, os, pkgutil, tempfile
from decimal import Decimal
from threading import Lock
from .util.async_widget import bind_widget_to_value
from .amp import features
from .common.config import config, ConfigDict, CONFDIR
from .protocol import getProtocols
from . import Amp, NAME, VERSION, AUTHOR


TITLE = "%s Control Menu"%NAME
os.environ["KIVY_NO_ARGS"] = "1"
parser = argparse.ArgumentParser(description='Control Menu App')
parser.add_argument('--protocol', type=str, default=None, help='Amp protocol')
parser.add_argument('--verbose', '-v', action='count', default=0, help='Verbose mode')
args = parser.parse_args()


from kivy.app import App
from kivy.lang import Builder
from kivy.clock import Clock
from kivy.uix.gridlayout import GridLayout
from kivy.uix.stacklayout import StackLayout
from kivy.uix.slider import Slider
from kivy.uix.label import Label
from kivy.uix.tabbedpanel import TabbedPanelItem, TabbedPanelHeader
from kivy.uix.button import Button
from kivy.uix.tabbedpanel import TabbedPanel
from kivy.uix.scrollview import ScrollView
from kivy.uix.dropdown import DropDown


class TabPanel(ScrollView):
    config = ConfigDict("menu.json")

    def __init__(self, amp, tabbed_panel):
        self.tabbed_panel = tabbed_panel
        self.amp = amp
        super().__init__()
        self.features = {}
        self._features_stack = list(self.amp.features.items())
        Clock.schedule_once(lambda *_:self.addFeaturesFromStack(chunksize=50), .7)
        self.amp.preload_features = set(self.amp.features.keys())
        self.amp.bind(on_feature_change=self.on_feature_change)
        
    @property
    def header(self): return self.tabbed_panel.current_tab

    def addFeaturesFromStack(self, *_, chunksize=50):
        chunk, self._features_stack = self._features_stack[:chunksize], self._features_stack[chunksize:]
        for key, f in chunk:
            print("adding %s"%f.name)
            self.addFeature(key, f)
            if f.isset(): f.on_change(None, f.get())
        if self._features_stack: Clock.schedule_once(self.addFeaturesFromStack, .5)

    def addFeature(self, key, f):
        #self.features[key] = []
        row = FeatureRow()
        row.ids.text.text = f.name
        row.ids.checkbox.active = key in self.config["pinned"]

        if f.type == bool: w = self.addBoolFeature(f)
        elif f.type == str: w = self.addSelectFeature(f)
        elif f.type == int: w = self.addIntFeature(f)
        elif f.type == Decimal: w = self.addDecimalFeature(f)
        else: raise RuntimeError("Not implemented: Type '%s'"%f.type)
        if w: row.ids.content.add_widget(w)
        
        hide_widget(row)
        self.ids.layout.add_widget(row)
        
        def on_checkbox(checkbox, active):
            if active: self.config["pinned"].append(key)
            else: self.config["pinned"].remove(key)
            self.config.save()
            self.header.refresh_feature_visibility(f)
        row.ids.checkbox.bind(active=on_checkbox)

        self.features[key] = [row]
        
    def _addNumericFeature(self, f, from_widget=lambda n:n, step=None):
        panel = NumericFeature()
        if step: panel.ids.slider.step = step
        
        def get(inst, value): return from_widget(panel.ids.slider.value)
        def set(value):
            panel.ids.slider.range = (float(f.min), float(f.max))
            panel.ids.slider.value = float(value)
            panel.ids.label.text = str(float(value))

        on_change = self.bind_widget_to_feature(f,get,set)
        panel.ids.slider.bind(value=on_change)
        return panel
    
    def addIntFeature(self, f):
        return self._addNumericFeature(f, from_widget=lambda n:int(n), step=1)
        
    def addDecimalFeature(self, f):
        return self._addNumericFeature(f, step=.5)

    def addBoolFeature(self, f):
        bf = BoolFeature()
        
        def get(inst):
            return inst.value if inst.state == "down" else not inst.value
            
        def set(value):
            trans = {False: "normal", True: "down"}
            bf.ids.on.state = trans[value]
            bf.ids.off.state = trans[not value]

        on_change = self.bind_widget_to_feature(f,get,set)
        bf.ids.on.bind(on_press=on_change)
        bf.ids.off.bind(on_press=on_change)
        return bf

    def addSelectFeature(self, f):
        dropdown = SelectFeatureOptions()
        button = SelectFeature()
        button.bind(on_release=lambda i: dropdown.open(i))
        
        def get(inst, value): return value
        def set(value):
            button.text = value
            dropdown.clear_widgets()
            for text in f.options:
                o = SelectFeatureOption()
                o.text = text
                #o.bind(on_release=lambda i: dropdown.select(i.text))
                o.bind(on_press=lambda i: on_change(o,i.text))
                dropdown.add_widget(o)
            

        on_change = self.bind_widget_to_feature(f,get,set)
        #dropdown.bind(on_select=on_change)

        return button

    def on_feature_change(self, key, value, prev):
        if prev == None and isinstance(self.header, TabHeader):
            self.header.refresh_feature_visibility(self.amp.features[key])
            
    def bind_widget_to_feature(self, f, widget_getter, widget_setter):
        """ @f Feature object """
        on_value_change, on_widget_change = bind_widget_to_value(
            f.get, f.set, widget_getter, widget_setter)
        
        f.bind(on_change=on_value_change)
        return on_widget_change
        

class TabHeader(TabbedPanelHeader):

    def __init__(self, panel, *args, filter=None, **xargs):
        super().__init__(*args, **xargs)
        self.content = panel
        if filter: self.filter = filter
        self.bind(on_release = lambda *_: self.refresh_panel())
        
    def refresh_panel(self):
        for key, f in self.content.amp.features.items(): self.refresh_feature_visibility(f)
    
    def refresh_feature_visibility(self, f):
        if f.key not in self.content.features: return
        func = show_widget if f.isset() and self.filter(f) else hide_widget
        try:
            for w in self.content.features[f.key]: func(w)
        except RuntimeError: pass
        

class ScrollViewLayout(StackLayout):

    def __init__(self,*args,**xargs):
        super().__init__(*args,**xargs)
        self.bind(minimum_height=self.setter('height'))


class FeatureRow(GridLayout): pass

class NumericFeature(GridLayout): pass

class Base(StackLayout): pass

class SettingsTab(StackLayout): pass

class Waiting(StackLayout): pass

class BoolFeature(GridLayout): pass

class SelectFeature(Button): pass

class SelectFeatureOptions(DropDown): pass

class SelectFeatureOption(Button): pass

class PinnedTab(TabHeader):
    text = "Pinned"
    filter = lambda self,f: f.key in self.content.config["pinned"]

class AllTab(TabHeader):
    text = "All"
    filter = lambda self,f: True

class About(TabbedPanelItem):
    
    def __init__(self):
        super().__init__()
        self.ids.text.text = "%s Version %s\nCopyright (C) 2020 %s"%(NAME, VERSION, AUTHOR)


class SettingsTab(TabbedPanelItem):

    def __init__(self, parent):
        super().__init__()
        self._parent = parent
        self._protocols = getProtocols()

        dropdown = SelectFeatureOptions()
        self.ids.protocol.bind(on_release=lambda i: dropdown.open(i))
        for i,(text, module) in enumerate(self._protocols):
            o = SelectFeatureOption()
            o.text = text
            o.bind(on_release=lambda e,i=i: dropdown.select(i))
            dropdown.add_widget(o)
        
        def on_select(e,i): 
            self.ids.protocol.text, module = self._protocols[i]
            self.protocol = module.__name__
        dropdown.bind(on_select=on_select)
        
        self.ids.host.text = config.get("Amp","host")
        self.ids.port.text = config.get("Amp","port")
        self.ids.protocol.text = config.get("Amp","protocol")
        self.protocol = config.get("Amp","protocol")

    def apply(self):
        config["Amp"]["host"] = self.ids.host.text
        config["Amp"]["port"] = self.ids.port.text
        config["Amp"]["protocol"] = self.protocol
        self._parent.change_amp()


def get_menu(app, **kwargs):
    try: amp = Amp(connect=False, verbose=args.verbose, **kwargs)
    except Exception as e:
        print(repr(e))
        return Menu2(app)
    else: return Menu1(app, amp=amp)


class _Menu(TabbedPanel):

    def __init__(self, app, amp=None, **kwargs):
        super().__init__()
        self.app = app
        self.amp = amp
        self.build()

    def build(self):
        self.settings_tab = SettingsTab(self)
        self.add_widget(self.settings_tab)
        self.add_widget(About())
        self.app.root.clear_widgets()
        self.app.root.add_widget(self)

    def change_amp(self, *args, **xargs):
        self.app.clear()
        if self.amp: self.amp.exit()
        Clock.schedule_once(lambda *_:get_menu(self.app, *args, **xargs), 1)


class Menu2(_Menu):

    def build(self):
        super().build()
        self.default_tab = self.settings_tab
        self.default_tab_text = self.settings_tab.text
        

class Menu1(_Menu):

    def build(self):
        self.app.title = "%s – %s"%(TITLE, self.amp.name)
        tabs = {}
        self.panel = TabPanel(self.amp, self)
        self.pinned_tab = PinnedTab(self.panel)
        self.all_tab = AllTab(self.panel)
        self.add_widget(self.pinned_tab)
        self.add_widget(self.all_tab)
        for key, f in self.amp.features.items():
            if f.category not in tabs: tabs[f.category] = self._newTab(f.category)
        super().build()
        self.default_tab = self.pinned_tab
        self.default_tab_text = self.pinned_tab.text
        self.pinned_tab.refresh_panel()
        self.amp.enter()
        
    def _newTab(self, category):
        def filter(f, category=category): return f.category == category
        header = TabHeader(self.panel, text=category, filter=filter)
        self.add_widget(header)
        return header


def show_widget(w):
    old_attrs = getattr(w,"_attrs",None)
    if old_attrs:
        w.height, w.size_hint_y, w.opacity, w.disabled = old_attrs
        del w._attrs
    
def hide_widget(w):
    if hasattr(w, "_attrs"): raise RuntimeError(
        "Widget's attribute '_attrs' is occupied or widget is already hidden!")
    w._attrs = w.height, w.size_hint_y, w.opacity, w.disabled
    w.height = 0
    w.size_hint_y = None
    w.opacity = 0
    w.disabled = True


class App(App):
    
    def build(self):
        self.title = TITLE
        root = Base()
        root.add_widget(Waiting())
        return root

    def on_start(self, **xargs):
        Clock.schedule_once(lambda *_:get_menu(self, protocol=args.protocol), 1)

    def clear(self):
        self.root.clear_widgets()
        self.root.add_widget(Waiting())


kv = pkgutil.get_data(__name__,"share/menu.kv").decode()
Builder.load_string(kv)


def main():
    icon_path = tempfile.mktemp()
    try:
        with open(icon_path, "wb") as fp:
            fp.write(pkgutil.get_data(__name__,"share/icons/scalable/logo.svg"))
        app = App()
        app.icon = icon_path
        app.run()
    finally:
        try: app.root.children[0].amp.exit()
        except: pass
        os.remove(icon_path)


if __name__ == "__main__": main()

