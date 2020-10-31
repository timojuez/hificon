from kivy.app import App
from kivy.uix.gridlayout import GridLayout
from kivy.uix.slider import Slider
from kivy.uix.label import Label
from kivy.uix.tabbedpanel import TabbedPanelItem
from kivy.uix.switch import Switch
from kivy.uix.button import Button
from kivy.uix.tabbedpanel import TabbedPanel
from kivy.uix.scrollview import ScrollView
from kivy.uix.dropdown import DropDown

from threading import Lock
from ..amp import features
from ..config import config
from .. import Amp, NAME


def bind_widget_to_value(value_getter, value_setter, widget_getter, widget_setter):
    """
    Binds a widget with given getter and setter asynchronously to a value so that 
        the widget always stays synchronised with the value.
    Returns the functions that shall be called when the value resp. widget changes
    @value_getter: callable
    @value_setter: callable(new value)
    @widget_getter: callable
    @widget_setter: callable(new value)
    @returns: (callable on_variable_change, callable on_widget_change)
        on_value_change(*a) will call get_from_widget(*a)
    """
    lock = Lock()
    def on_widget_change(*args):
        if lock.locked(): return
        new = widget_getter(*args)
        with lock: widget_setter(value_getter())
        try: value_setter(new)
        except Exception as e: print(repr(e))
    def on_value_change(old, new):
        with lock: widget_setter(new)
    return on_value_change, on_widget_change

def bind_widget_to_feature(f, widget_getter, widget_setter):
    """ @f Feature object """
    on_value_change, on_widget_change = bind_widget_to_value(
        f.get, f.set, widget_getter, widget_setter)
    
    widget_setter(f.get())
    f.bind(on_change=on_value_change)
    return on_widget_change
    

class TabPanel(TabbedPanelItem): pass

class ScrollViewLayout(GridLayout):

    def __init__(self,*args,**xargs):
        super().__init__(*args,**xargs)
        self.bind(minimum_height=self.setter('height'))


class FeatureRow(GridLayout): pass

class NumericFeature(GridLayout): pass

class BoolFeature(Switch): pass

class SelectFeature(Button): pass

class SelectFeatureOptions(DropDown): pass

class SelectFeatureOption(Button): pass


class Menu(TabbedPanel):

    def __init__(self, amp, **kwargs):
        super().__init__(**kwargs)
        tabs = {}
        self.pinned = config.getlist("GUI","pinned")
        self.features = {}
        for key, f in amp.features.items():
            @features.require(key, timeout=None)
            def add(amp, key, f):
                print("adding %s"%f.name)
                if f.category not in tabs: tabs[f.category] = self._newTab(f.category)
                self.addFeature(key, f, tabs[f.category])
            add(amp, key, f)

    def _newTab(self, title):
        panel = TabPanel()
        panel.text = title
        self.add_widget(panel)
        return panel.ids.layout

    def addFeature(self, key, f, tab):
        self.features[key] = {"panel":None, "checkboxes":{"lock":Lock(),"objects":[]}}
        self.features[key]["panel"] = self._addFeatureToTab(key,f,self.ids.pinned.ids.layout)
        if key not in self.pinned: hide_widget(self.features[key]["panel"])
        self._addFeatureToTab(key,f,tab)
        self._addFeatureToTab(key,f,self.ids.all.ids.layout)
        with self.features[key]["checkboxes"]["lock"]:
            for c in self.features[key]["checkboxes"]["objects"]: c.active = key in self.pinned
        
    def _addFeatureToTab(self, key, f, tab):
        row = FeatureRow()
        row.ids.text.text = f.name

        if f.type == bool: w = self.addBoolFeature(f)
        elif f.type == str: w = self.addSelectFeature(f)
        elif f.type == int: w = self.addIntFeature(f)
        elif f.type == float: w = self.addFloatFeature(f)
        else: raise RuntimeError("Not implemented: Type '%s'"%f.type)
        if w: row.ids.content.add_widget(w)
        
        tab.add_widget(row)
        
        def on_checkbox(checkbox, active):
            if self.features[key]["checkboxes"]["lock"].locked(): return
            if active: self.pinned.append(key)
            else: self.pinned.remove(key)
            config.setlist("GUI", "pinned", self.pinned)
            config.save()
            with self.features[key]["checkboxes"]["lock"]:
                if active: show_widget(self.features[key]["panel"])
                else: hide_widget(self.features[key]["panel"])
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
            panel.ids.slider.range = (f.min, f.max)
            panel.ids.slider.value = value
            panel.ids.label.text = str(value)

        on_change = bind_widget_to_feature(f,get,set)
        panel.ids.slider.bind(value=on_change)
        return panel
    
    def addIntFeature(self, f):
        return self._addNumericFeature(f, from_widget=lambda n:int(n), step=1)
        
    def addFloatFeature(self, f):
        return self._addNumericFeature(f, step=.5)

    def addBoolFeature(self, f):
        switch = Switch()
        lock = Lock()
        
        def get(inst, value): return switch.active
        def set(value): switch.active = value

        on_change = bind_widget_to_feature(f,get,set)
        switch.bind(active=on_change)
        return switch

    def addSelectFeature(self, f):
        dropdown = SelectFeatureOptions()
        for text in f.options:
            o = SelectFeatureOption()
            o.text = text
            #o.bind(on_release=lambda i: dropdown.select(i.text))
            o.bind(on_release=lambda i: on_change(o,i.text))
            dropdown.add_widget(o)
        
        button = SelectFeature()
        button.bind(on_release=lambda i: dropdown.open(i))
        
        def get(inst, value): return value
        def set(value): button.text = value

        on_change = bind_widget_to_feature(f,get,set)
        #dropdown.bind(on_select=on_change)

        return button


def show_widget(w):
    old_attrs = getattr(w,"_attrs",None)
    if old_attrs: w.height, w.size_hint_y, w.opacity, w.disabled = old_attrs
    
def hide_widget(w):
    w._attrs = w.height, w.size_hint_y, w.opacity, w.disabled
    w.height = 0
    w.size_hint_y = None
    w.opacity = 0
    w.disabled = True


class App(App):
    kv_file = "../share/menu.kv"
    
    def build(self):
        widgetContainer = Menu(amp)
        self.title = "%(name)s Control Menu – %(amp)s"%dict(name=NAME, amp=amp.name)
        return widgetContainer
        
        
#amp = Amp(verbose=15)
amp = Amp(protocol=".emulator",verbose=15)
with amp:
    app = App()
    app.run()


