import argparse, os, pkgutil, tempfile
from decimal import Decimal
from threading import Lock
from .util.async_widget import bind_widget_to_value
from .amp import features
from .common.config import config, ConfigDict, CONFDIR
from . import Amp, NAME, VERSION, AUTHOR


os.environ["KIVY_NO_ARGS"] = "1"
parser = argparse.ArgumentParser(description='Control Menu App')
parser.add_argument('--protocol', type=str, default=None, help='Amp protocol')
parser.add_argument('--verbose', '-v', action='count', default=0, help='Verbose mode')
args = parser.parse_args()


from kivy.app import App
from kivy.lang import Builder
from kivy.uix.gridlayout import GridLayout
from kivy.uix.stacklayout import StackLayout
from kivy.uix.slider import Slider
from kivy.uix.label import Label
from kivy.uix.tabbedpanel import TabbedPanelItem
from kivy.uix.button import Button
from kivy.uix.tabbedpanel import TabbedPanel
from kivy.uix.scrollview import ScrollView
from kivy.uix.dropdown import DropDown



class TabPanel(TabbedPanelItem): pass

class ScrollViewLayout(StackLayout):

    def __init__(self,*args,**xargs):
        super().__init__(*args,**xargs)
        self.bind(minimum_height=self.setter('height'))


class FeatureRow(GridLayout): pass

class NumericFeature(GridLayout): pass

class BoolFeature(StackLayout): pass

class SelectFeature(StackLayout): pass

class SelectFeatureOptions(DropDown): pass

class SelectFeatureOption(Button): pass

class About(TabbedPanelItem):
    
    def __init__(self):
        super().__init__()
        self.ids.text.text = "%s Version %s\nCopyright (C) 2020 %s"%(NAME, VERSION, AUTHOR)


"""
class CustomFeature:
    def isset(self): return True
    def bind(self,*args,**xargs): pass

class ControlPowerOn(CustomFeature):
    name = "Auto Power On"
    category = NAME
    type = bool
    def get(self): return config.getboolean("Amp","control_power_on")
    def set(self, value): config["Amp"]["control_power_on"] = str(int(bool(value)))

custom_menu = dict(_power_on = ControlPowerOn())
"""
custom_menu = {}


class Menu(TabbedPanel):
    config = ConfigDict("menu.json")

    def __init__(self, amp, **kwargs):
        super().__init__(**kwargs)
        tabs = {}
        self.features = {}
        for key, f in {**amp.features, **custom_menu}.items():
            print("adding %s"%f.name)
            if f.category not in tabs: tabs[f.category] = self._newTab(f.category)
            self.addFeature(key, f, tabs[f.category])
            if f.isset(): # show static features
                self.show_row(amp, key, f)
                f.on_change(None, f.get())
        amp.preload_features = set(amp.features.keys())
        amp.bind(on_feature_change=self.on_feature_change)
        self.add_widget(About())

    def show_row(self, amp, key, f):
        print("Showing %s"%f.name)
        for w in self.features[key]["rows"]: show_widget(w)
        if key not in self.config["pinned"]: hide_widget(self.features[key]["pinned_row"])

    def _newTab(self, title):
        panel = TabPanel()
        panel.text = title
        self.add_widget(panel)
        return panel.ids.layout

    def addFeature(self, key, f, tab):
        self.features[key] = {"rows":[], "pinned_row":None, 
            "checkboxes":{"lock":Lock(),"objects":[]}}
        self.features[key]["pinned_row"] = self._addFeatureToTab(key,f,self.ids.pinned.ids.layout)
        self._addFeatureToTab(key,f,tab)
        self._addFeatureToTab(key,f,self.ids.all.ids.layout)
        with self.features[key]["checkboxes"]["lock"]:
            for c in self.features[key]["checkboxes"]["objects"]: c.active = key in self.config["pinned"]
        
    def _addFeatureToTab(self, key, f, tab):
        row = FeatureRow()
        row.ids.text.text = f.name

        if f.type == bool: w = self.addBoolFeature(f)
        elif f.type == str: w = self.addSelectFeature(f)
        elif f.type == int: w = self.addIntFeature(f)
        elif f.type == Decimal: w = self.addDecimalFeature(f)
        else: raise RuntimeError("Not implemented: Type '%s'"%f.type)
        if w: row.ids.content.add_widget(w)
        
        hide_widget(row)
        tab.add_widget(row)
        self.features[key]["rows"].append(row)
        
        def on_checkbox(checkbox, active):
            if self.features[key]["checkboxes"]["lock"].locked(): return
            if active: self.config["pinned"].append(key)
            else: self.config["pinned"].remove(key)
            self.config.save()
            with self.features[key]["checkboxes"]["lock"]:
                if active: show_widget(self.features[key]["pinned_row"])
                else: hide_widget(self.features[key]["pinned_row"])
                for c in self.features[key]["checkboxes"]["objects"]:
                    c.active = active
        row.ids.checkbox.bind(active=on_checkbox)
        
        self.features[key]["checkboxes"]["objects"].append(row.ids.checkbox)
        return row
        
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
        layout = SelectFeature()
        layout.ids.button.bind(on_release=lambda i: dropdown.open(i))
        
        def get(inst, value): return value
        def set(value):
            layout.ids.button.text = value
            dropdown.clear_widgets()
            for text in f.options:
                o = SelectFeatureOption()
                o.text = text
                #o.bind(on_release=lambda i: dropdown.select(i.text))
                o.bind(on_press=lambda i: on_change(o,i.text))
                dropdown.add_widget(o)
            

        on_change = self.bind_widget_to_feature(f,get,set)
        #dropdown.bind(on_select=on_change)

        return layout

    def on_feature_change(self, key, value, prev):
        if prev == None and key and key in self.features:
            self.show_row(amp, key, amp.features[key])
            
    def bind_widget_to_feature(self, f, widget_getter, widget_setter):
        """ @f Feature object """
        on_value_change, on_widget_change = bind_widget_to_value(
            f.get, f.set, widget_getter, widget_setter)
        
        f.bind(on_change=on_value_change)
        return on_widget_change


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
        self.title = "%(name)s Control Menu – %(amp)s"%dict(name=NAME, amp=amp.name)
        return menu


kv = pkgutil.get_data(__name__,"share/menu.kv").decode()
Builder.load_string(kv)


def main():
    global amp, menu
    
    amp = Amp(connect=False, protocol=args.protocol, verbose=args.verbose)
    menu = Menu(amp)

    icon_path = tempfile.mktemp()
    try:
        with open(icon_path, "wb") as fp:
            fp.write(pkgutil.get_data(__name__,"share/icons/scalable/logo.svg"))
        with amp:
            app = App()
            app.icon = icon_path
            app.run()
    finally:
        os.remove(icon_path)


if __name__ == "__main__": main()
