import argparse, os, pkgutil, tempfile, sys, traceback
from decimal import Decimal
from .core.util.async_widget import bind_widget_to_value
from .core import features
from .core.config import config, ConfigDict, CONFDIR
from . import Target, get_protocols, NAME, VERSION, AUTHOR, COPYRIGHT


TITLE = f"{NAME} Control Menu"
os.environ["KIVY_NO_ARGS"] = "1"
parser = argparse.ArgumentParser(description=TITLE)
parser.add_argument('-t', '--target', metavar="URI", type=str, default=None, help='Target URI')
parser.add_argument('--verbose', '-v', action='count', default=0, help='Verbose mode')
cmd_args = parser.parse_args()


from kivy.app import App
from kivy.lang import Builder
from kivy.clock import Clock
from kivy.uix.gridlayout import GridLayout
from kivy.uix.stacklayout import StackLayout
from kivy.uix.slider import Slider
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.scrollview import ScrollView
from kivy.uix.dropdown import DropDown
from kivy.uix.screenmanager import ScreenManager, Screen


class TabPanel(ScrollView):
    config = ConfigDict("menu.json")
    filter = None

    def __init__(self, target):
        self.target = target
        super().__init__()
        self.features = {}
        pinned = {True:[], False:[]}
        for f in self.target.features.values(): pinned[f.key in self.config["pinned"]].append(f)
        self._features_stack = [*pinned[True], *pinned[False]]
        self.addFeaturesFromStack(chunksize=50, repeat=None)
        
    def addFeaturesFromStack(self, *_, chunksize=1, repeat=.1):
        chunk, self._features_stack = self._features_stack[:chunksize], self._features_stack[chunksize:]
        for f in chunk:
            print("adding %s"%f.name)
            self.addFeature(f)
        if repeat and self._features_stack: Clock.schedule_once(self.addFeaturesFromStack, repeat)

    def addFeature(self, f):
        self.target.preload_features.add(f.key)
        if self.target.connected:
            try: f.async_poll()
            except ConnectionError: pass
        row = FeatureRow()
        row.ids.text.text = f.name
        row.ids.checkbox.active = f.key in self.config["pinned"]

        if f.type == bool: w = self.addBoolFeature(f)
        elif f.type == str: w = self.addSelectFeature(f)
        elif f.type == int: w = self.addIntFeature(f)
        elif f.type == Decimal: w = self.addDecimalFeature(f)
        else: return print("WARNING: Not implemented: Feature type '%s'"%f.type, file=sys.stderr)
        if w: row.ids.content.add_widget(w)
        
        def on_checkbox(checkbox, active):
            if active: self.config["pinned"].append(f.key)
            else: self.config["pinned"].remove(f.key)
            self.config.save()
            self.update_feature_visibility(f)
        row.ids.checkbox.bind(active=on_checkbox)

        self.features[f.key] = row
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
        if self.filter is None: return
        func = show_widget if f.isset() and self.filter(f) else hide_widget
        try: func(self.features[f.key])
        except RuntimeError: pass
        
    def bind_widget_to_feature(self, f, widget_getter, widget_setter):
        """ @f Feature object """
        on_value_change, on_widget_change = bind_widget_to_value(
            f.get, f.send, widget_getter, widget_setter)
        f.bind(on_value_change)
        return on_widget_change


class TabHeader(ToggleButton):
    """ a tab header. shows self.panel when activated """

    def __init__(self, menu, *args, **xargs):
        super().__init__(*args, **xargs, group = "tab_header")
        self.content = menu.ids.menu_content
        self.bind(on_release = lambda *_: self.activate())

    def activate(self):
        self.state = "down"
        self.content.clear_widgets()
        self.content.add_widget(self.panel)


class CategoryTabHeader(TabHeader):

    def __init__(self, menu, *args, filter=None, **xargs):
        super().__init__(menu, *args, **xargs)
        self.panel = menu.panel
        if filter: self.filter = filter
        self.bind(on_release = lambda *_: self.refresh_panel())
        
    def refresh_panel(self):
        self.panel.filter = self.filter
        for key in self.panel.features.keys():
            self.panel.update_feature_visibility(self.panel.target.features[key])


class SettingsTabHeader(TabHeader):

    def __init__(self, *args, **xargs):
        super().__init__(*args, **xargs)
        self.panel = SettingsTab()


class AboutTabHeader(TabHeader):

    def __init__(self, *args, **xargs):
        super().__init__(*args, **xargs)
        self.panel = AboutTab()


class ScrollViewLayoutVertical(StackLayout):

    def __init__(self,*args,**xargs):
        super().__init__(*args,**xargs)
        self.bind(minimum_height=self.setter('height'))


class ScrollViewLayoutHorizontal(GridLayout):

    def __init__(self,*args,**xargs):
        super().__init__(*args,**xargs)
        self.bind(minimum_width=self.setter('width'))


class MyGrid(GridLayout): pass

class FeatureRow(MyGrid): pass

class NumericFeature(GridLayout): pass

class SettingsTab(StackLayout): pass

class BoolFeature(GridLayout): pass

class SelectFeature(Button): pass

class SelectFeatureOptions(DropDown): pass

class SelectFeatureOption(Button): pass

class PinnedTab(CategoryTabHeader):
    text = "Pinned"
    filter = lambda self,f: f.key in self.panel.config["pinned"]

class AllTab(CategoryTabHeader):
    text = "All"
    filter = lambda self,f: True

class AboutTab(StackLayout):
    
    def __init__(self):
        super().__init__()
        self.ids.text.text = f"{TITLE}\nVersion {VERSION}\n{COPYRIGHT}\n"


class SettingsTab(StackLayout):

    def __init__(self):
        super().__init__()
        protocol_names = {P.protocol: P.get_title() for P in get_protocols()}
        dropdown = SelectFeatureOptions()
        self.ids.protocol.bind(on_release=lambda i: dropdown.open(i))
        for protocol, title in protocol_names.items():
            o = SelectFeatureOption()
            o.text = title
            o.bind(on_release=lambda e,protocol=protocol: dropdown.select(protocol))
            dropdown.add_widget(o)
        
        def on_select(e,protocol):
            self.protocol = protocol
            self.ids.protocol.text = protocol_names.get(protocol, protocol)
        dropdown.bind(on_select=on_select)
        
        uri = config.get("Target","uri").split(":")
        try:
            on_select(None, uri[0])
            self.ids.host.text = uri[1]
            self.ids.port.text = uri[2]
        except IndexError: pass

    def apply(self):
        parts = [self.protocol, self.ids.host.text.strip(), self.ids.port.text.strip()]
        config["Target"]["uri"] = ":".join(parts)
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

    def __init__(self, target=None, **kwargs):
        super().__init__()
        self.target = target
        #self.build()
        Clock.schedule_once(lambda *_:self.build(), .8) # TODO: instead do this on WelcomeScreen.on_enter. must be executed by Clock!

    def build(self):
        """ is being executed while showing Welcome screen """
        self.settings_tab = SettingsTabHeader(self)
        self.ids.headers.add_widget(self.settings_tab)
        self.ids.headers.add_widget(AboutTabHeader(self))
        App.get_running_app().manager.switch_to(self)
        

class ErrorScreen(_MenuScreen):

    def build(self):
        super().build()
        self.settings_tab.activate()
        

class MenuScreen(_MenuScreen):
    
    def __init__(self, *args, **xargs):
        super().__init__(*args, **xargs)
        self.target.features.name.bind(self.set_title)
        self.target.enter()
    
    def set_title(self, name):
        App.get_running_app().title = "%s – %s"%(TITLE, name)
    
    def build(self):
        self.panel = TabPanel(self.target)
        self.pinned_tab = PinnedTab(self)
        self.all_tab = AllTab(self)
        self.ids.headers.add_widget(self.pinned_tab)
        self.ids.headers.add_widget(self.all_tab)
        categories = list(dict.fromkeys([f.category for f in self.target.features.values()]))
        tabs = {}
        def silently_hide_widget(e):
            try: return hide_widget(e)
            except RuntimeError: pass
        for cat in categories:
            e = self._newTab(cat)
            tabs[cat] = e
            hide_widget(e)
            self.target.bind(on_disconnected = lambda e=e:silently_hide_widget(e))
        for key, f in self.target.features.items():
            f.bind(on_set = lambda cat=f.category: show_widget(tabs[cat]))
        super().build()
        self.pinned_tab.activate()

    def _newTab(self, category):
        def filter(f, category=category): return f.category == category
        header = CategoryTabHeader(self, text=category, filter=filter)
        self.ids.headers.add_widget(header)
        return header

    def on_enter(self): self.panel.addFeaturesFromStack()
        
    def on_leave(self): self.target.exit()


def show_widget(w):
    old_attrs = getattr(w,"_attrs",None)
    if old_attrs:
        w.height, w.size_hint_y, w.opacity, w.disabled, w.width, w.size_hint_x = old_attrs
        del w._attrs
    
def hide_widget(w):
    if hasattr(w, "_attrs"): raise RuntimeError(
        "Widget's attribute '_attrs' is occupied or widget is already hidden!")
    w._attrs = w.height, w.size_hint_y, w.opacity, w.disabled, w.width, w.size_hint_x
    w.height = 0
    w.width = 0
    w.size_hint_x = None
    w.size_hint_y = None
    w.opacity = 0
    w.disabled = True


class App(App):

    def load_screen(self, *args, **xargs):
        self.title = TITLE
        self.manager.switch_to(WelcomeScreen())
        try: self.target = Target(*args, connect=False, verbose=cmd_args.verbose, **xargs)
        except Exception as e:
            print(traceback.format_exc())
            ErrorScreen()
        else: MenuScreen(self.target)

    def build(self):
        self.manager = ScreenManager()
        self.load_screen(cmd_args.target)
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
        try: app.target.exit()
        except: pass
        os.remove(icon_path)


if __name__ == "__main__": main()

