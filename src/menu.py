import argparse, os, pkgutil, tempfile
from decimal import Decimal
from .util.async_widget import bind_widget_to_value
from .amp import features
from .common.config import config, ConfigDict, CONFDIR
from .protocol import protocols
from . import Amp, Amp_cls, NAME, VERSION, AUTHOR, COPYRIGHT


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
from kivy.uix.screenmanager import ScreenManager, Screen


class TabPanel(ScrollView):
    config = ConfigDict("menu.json")

    def __init__(self, amp, tabbed_panel):
        self.tabbed_panel = tabbed_panel
        self.amp = amp
        super().__init__()
        self.features = {}
        self._features_stack = list(self.amp.features.items())
        self.addFeaturesFromStack(chunksize=50, repeat=None)
        
    @property
    def header(self): return self.tabbed_panel.current_tab

    def addFeaturesFromStack(self, *_, chunksize=15, repeat=.2):
        chunk, self._features_stack = self._features_stack[:chunksize], self._features_stack[chunksize:]
        for key, f in chunk:
            print("adding %s"%f.name)
            self.addFeature(key, f)
        if repeat and self._features_stack: Clock.schedule_once(self.addFeaturesFromStack, repeat)

    def addFeature(self, key, f):
        try: f.async_poll()
        except ConnectionError: pass
        row = FeatureRow()
        row.ids.text.text = f.name
        row.ids.checkbox.active = key in self.config["pinned"]

        if f.type == bool: w = self.addBoolFeature(f)
        elif f.type == str: w = self.addSelectFeature(f)
        elif f.type == int: w = self.addIntFeature(f)
        elif f.type == Decimal: w = self.addDecimalFeature(f)
        else: raise RuntimeError("Not implemented: Type '%s'"%f.type)
        if w: row.ids.content.add_widget(w)
        
        def on_checkbox(checkbox, active):
            if active: self.config["pinned"].append(key)
            else: self.config["pinned"].remove(key)
            self.config.save()
            self.update_feature_visibility(f)
        row.ids.checkbox.bind(active=on_checkbox)

        self.features[key] = row
        f.bind(on_set=lambda: self.update_feature_visibility(f))
        f.bind(on_unset=lambda: self.update_feature_visibility(f))
        self.ids.layout.add_widget(row)
        
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
            Clock.schedule_once(lambda *_:update_options(), 0)
        
        def update_options():
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

    def update_feature_visibility(self, f):
        Clock.schedule_once(lambda *_,f=f: self._update_feature_visibility(f), -1)
        
    def _update_feature_visibility(self, f):
        filter = getattr(self.header, "filter", None)
        if filter is None: return
        func = show_widget if f.isset() and filter(f) else hide_widget
        try: func(self.features[f.key])
        except RuntimeError: pass
        
    def bind_widget_to_feature(self, f, widget_getter, widget_setter):
        """ @f Feature object """
        on_value_change, on_widget_change = bind_widget_to_value(
            f.get, f.set, widget_getter, widget_setter)
        f.bind(on_value_change)
        return on_widget_change
        

class TabHeader(TabbedPanelHeader):

    def __init__(self, panel, *args, filter=None, **xargs):
        super().__init__(*args, **xargs)
        self.content = panel
        if filter: self.filter = filter
        self.bind(on_release = lambda *_: self.refresh_panel())
        
    def refresh_panel(self):
        for key in self.content.features.keys():
            self.content.update_feature_visibility(self.content.amp.features[key])


class ScrollViewLayout(StackLayout):

    def __init__(self,*args,**xargs):
        super().__init__(*args,**xargs)
        self.bind(minimum_height=self.setter('height'))


class MyGrid(GridLayout): pass

class FeatureRow(MyGrid): pass

class NumericFeature(GridLayout): pass

class SettingsTab(StackLayout): pass

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
        self.ids.text.text = f"{NAME} Control Menu\nVersion {VERSION}\n{COPYRIGHT}\n"


class SettingsTab(TabbedPanelItem):

    def __init__(self):
        super().__init__()
        protocol_names = {protocol_: Amp_cls(protocol_).protocol or protocol_
            for protocol_ in protocols}

        dropdown = SelectFeatureOptions()
        self.ids.protocol.bind(on_release=lambda i: dropdown.open(i))
        for protocol, text in protocol_names.items():
            o = SelectFeatureOption()
            o.text = text
            o.bind(on_release=lambda e,protocol=protocol: dropdown.select(protocol))
            dropdown.add_widget(o)
        
        def on_select(e,protocol):
            self.protocol = protocol
            self.ids.protocol.text = protocol_names.get(protocol, protocol)
        dropdown.bind(on_select=on_select)
        
        self.ids.host.text = config.get("Amp","host")
        self.ids.port.text = config.get("Amp","port")
        on_select(None, config.get("Amp","protocol"))

    def apply(self):
        config["Amp"]["host"] = self.ids.host.text.strip()
        config["Amp"]["port"] = self.ids.port.text.strip()
        config["Amp"]["protocol"] = self.protocol
        App.get_running_app().load_screen()


class WelcomeScreen(Screen):

    def __init__(self, *args, **xargs):
        super().__init__(*args, **xargs)
        fd, icon_path = tempfile.mkstemp()
        with open(fd, "wb") as fp:
            fp.write(pkgutil.get_data(__name__,"share/icons/png/logo.png"))
        self.ids.image.source = icon_path
        os.remove(icon_path)
        

class _MenuScreen(Screen):

    def __init__(self, amp=None, **kwargs):
        super().__init__()
        self.amp = amp
        self.tabs = TabbedPanel()
        #self.build()
        Clock.schedule_once(lambda *_:self.build(), .8) # TODO: instead do this on WelcomeScreen.on_enter. must be executed by Clock!

    def build(self):
        """ is being executed while showing Welcome screen """
        self.settings_tab = SettingsTab()
        self.tabs.add_widget(self.settings_tab)
        self.tabs.add_widget(About())
        self.add_widget(self.tabs)
        App.get_running_app().manager.switch_to(self)
        

class ErrorScreen(_MenuScreen):

    def build(self):
        super().build()
        self.tabs.default_tab = self.settings_tab
        self.tabs.default_tab_text = self.settings_tab.text
        

class MenuScreen(_MenuScreen):
    
    def __init__(self, *args, **xargs):
        super().__init__(*args, **xargs)
        self.amp.features.name.bind(self.set_title)
        self.amp.enter()
    
    def set_title(self, name):
        App.get_running_app().title = "%s – %s"%(TITLE, name)
    
    def build(self):
        headers = {}
        self.panel = TabPanel(self.amp, self.tabs)
        self.pinned_tab = PinnedTab(self.panel)
        self.all_tab = AllTab(self.panel)
        self.tabs.add_widget(self.pinned_tab)
        self.tabs.add_widget(self.all_tab)
        for key, f in self.amp.features.items():
            if f.category not in headers: headers[f.category] = self._newTab(f.category)
        super().build()
        self.tabs.default_tab = self.pinned_tab
        self.tabs.default_tab_text = self.pinned_tab.text
        self.pinned_tab.refresh_panel()
    
    def _newTab(self, category):
        def filter(f, category=category): return f.category == category
        header = TabHeader(self.panel, text=category, filter=filter)
        self.tabs.add_widget(header)
        return header

    def on_enter(self): self.panel.addFeaturesFromStack()
        
    def on_leave(self): self.amp.exit()


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

    def load_screen(self, **xargs):
        self.title = TITLE
        self.manager.switch_to(WelcomeScreen())
        try: self.amp = Amp(connect=False, verbose=args.verbose, **xargs)
        except Exception as e:
            print(repr(e))
            ErrorScreen()
        else: MenuScreen(self.amp)

    def build(self):
        self.manager = ScreenManager()
        self.load_screen(protocol = args.protocol)
        return self.manager


kv = pkgutil.get_data(__name__,"share/menu.kv").decode()
Builder.load_string(kv)


def main():
    fd, icon_path = tempfile.mkstemp()
    try:
        with open(fd, "wb") as fp:
            fp.write(pkgutil.get_data(__name__,"share/icons/scalable/logo.svg"))
        app = App()
        app.icon = icon_path
        app.run()
    finally:
        try: app.amp.exit()
        except: pass
        os.remove(icon_path)


if __name__ == "__main__": main()

