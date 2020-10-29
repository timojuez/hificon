import wx
from threading import Timer
from ..amp import features
from .. import Amp, NAME
from .menu import Frame
from . import CallAfter

RIGHTCOL=2


class Frame(Frame):

    def __init__(self, amp, parent=None):
        super().__init__(parent)
        self.SetTitle(self.GetTitle()%dict(name=NAME, amp=amp.name))
        panes = {}
        self.features = {}
        for key, f in amp.features.items():
            @features.require(key, timeout=None)
            @CallAfter
            def add(amp, key, f):
                print("adding %s"%f.name)
                if f.category not in panes: panes[f.category] = self._newPanel(f.category)
                self.addFeature(key, f, panes[f.category])
            add(amp, key, f)

    def _newPanel(self, title):
        m_collapsiblePane1 = wx.CollapsiblePane( self.content, wx.ID_ANY, title, wx.DefaultPosition, wx.DefaultSize, wx.CP_DEFAULT_STYLE|wx.VSCROLL|wx.CP_NO_TLW_RESIZE )
        m_collapsiblePane1.Collapse( True )
        box = wx.BoxSizer( wx.VERTICAL )

        m_collapsiblePane1.GetPane().SetSizer( box )
        m_collapsiblePane1.GetPane().Layout()
        box.Fit( m_collapsiblePane1.GetPane() )
        self.content.Sizer.Add( m_collapsiblePane1, 0, wx.EXPAND |wx.ALL, 5 )

        def on_collapse(event): self.Layout()
        m_collapsiblePane1.Bind( wx.EVT_COLLAPSIBLEPANE_CHANGED, on_collapse )
        return m_collapsiblePane1.GetPane()

    def addFeature(self, key, f, pane):
        self.features[key] = {"panel":None, "checkboxes":[]}
        self.features[key]["panel"] = self._addFeature(key,f,self.top_panel)
        self.features[key]["panel"].Hide()
        self.features[key]["panel"].Layout()
        self._addFeature(key,f,pane)
        self.Layout()
        
    def _addFeature(self, key, f, pane):
        panel = wx.Panel( pane, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.TAB_TRAVERSAL|wx.TRANSPARENT_WINDOW )

        box = wx.BoxSizer( wx.HORIZONTAL )
        panel.SetSizer( box )
        m_staticText5 = wx.StaticText( panel, wx.ID_ANY, f.name, wx.DefaultPosition, wx.Size( 60,-1 ), wx.ST_ELLIPSIZE_END )
        m_staticText5.Wrap( 1 )
        #m_staticText5.Wrap( -1 )

        panel.Sizer.Add( m_staticText5, 1, wx.ALL, 5 )

        if f.type == bool: on_feature_change, objs = self.addBoolFeature(f,panel)
        elif f.type == str: on_feature_change, objs = self.addSelectFeature(f,panel)
        elif f.type == int: on_feature_change, objs = self.addIntFeature(f,panel)
        elif f.type == float: on_feature_change, objs = self.addFloatFeature(f,panel)
        else: raise RuntimeError("Not implemented: Type '%s'"%f.type)

        m_checkBox = wx.CheckBox( panel, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.DefaultSize, 0 )
        m_checkBox.SetToolTip( u"highlight" )
        panel.Sizer.Add( m_checkBox, 0, wx.ALL, 5 )

        panel.Layout()
        box.Fit( panel )
        pane.Sizer.Add( panel, 1, wx.EXPAND |wx.ALL, 5 )
        
        def on_checkbox(event):
            getattr(self.features[key]["panel"],"Show" if m_checkBox.IsChecked() else "Hide")()
            for c in self.features[key]["checkboxes"]: 
                c.SetValue(m_checkBox.GetValue())
            self.Layout()
        
        m_checkBox.Bind( wx.EVT_CHECKBOX, on_checkbox )
        
        on_feature_change(None, f.get())
        f.bind(on_change=on_feature_change)
        self.features[key]["checkboxes"].append(m_checkBox)
        return panel
        
    def _addNumericFeature(self, f, panel, tostr=lambda n:"%d"%n, toint=lambda n:n, fromint=lambda n:n):
        sliderBox = wx.BoxSizer(wx.HORIZONTAL)
        slider = wx.Slider( panel, wx.ID_ANY, 0, -100, 100, wx.DefaultPosition, wx.DefaultSize, wx.SL_AUTOTICKS|wx.SL_HORIZONTAL )
        sliderBox.Add( slider, 1, wx.ALL, 5 )

        text = wx.StaticText( panel, wx.ID_ANY, u"0", wx.DefaultPosition, wx.DefaultSize, 0 )
        text.Wrap( -1 )

        sliderBox.Add( text, 0, wx.ALL, 5 )
        panel.Sizer.Add( sliderBox, RIGHTCOL, wx.ALL, 0 )

        timer = [False]
        candidate = []
        @CallAfter
        def on_feature_change(old, new):
            candidate.extend([1,])
            slider.SetValue(toint(new))
            slider.SetRange(toint(f.min), toint(f.max))
            text.SetLabel(tostr(new))
        def reload(): on_feature_change(None,f.get())
        def on_change(event):
            if candidate: return candidate.pop()
            old = f.get()
            new = fromint(slider.GetValue())
            try: f.set(new)
            except Exception as e:
                on_feature_change(None, f.get())
                print(repr(e))
            else:
                if timer[0]: timer[0].cancel()
                timer[0] = Timer(.5, reload)
                timer[0].start()
            
        slider.Bind( wx.EVT_COMMAND_SCROLL, on_change )
        return on_feature_change, (slider,text)
    
    def addIntFeature(self, f, panel):
        return self._addNumericFeature(f,panel)
        
    def addFloatFeature(self, f, panel):
        return self._addNumericFeature(f,panel,tostr=lambda n:"%0.1f"%n,toint=lambda n:n*2,fromint=lambda n:n/2)

    def addBoolFeature(self, f, panel):
        m_checkBox1 = wx.CheckBox( panel, wx.ID_ANY, u"", wx.DefaultPosition, wx.DefaultSize, 0 )
        panel.Sizer.Add( m_checkBox1, RIGHTCOL, wx.ALL, 5 )
        @CallAfter
        def on_feature_change(old, new): m_checkBox1.SetValue(new)
        @CallAfter
        def on_change(event):
            m_checkBox1.SetValue(not m_checkBox1.GetValue())
            f.set(not m_checkBox1.GetValue())
        m_checkBox1.Bind( wx.EVT_CHECKBOX, on_change )
        return on_feature_change, (m_checkBox1,)

    def addSelectFeature(self, f, panel):
        m_choice1 = wx.Choice( panel, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, f.options, 0 )
        m_choice1.SetSelection( 2 )
        panel.Sizer.Add( m_choice1, RIGHTCOL, wx.ALL, 5 )
        @CallAfter
        def on_feature_change(old, new):
            m_choice1.SetSelection(f.options.index(new) if new in f.options else wx.NOT_FOUND)
        def on_change(event):
            new = m_choice1.GetString(m_choice1.GetSelection())
            on_feature_change(None,f.get())
            f.set(new)
        m_choice1.Bind( wx.EVT_CHOICE, on_change )
        return on_feature_change, (m_choice1,)



app = wx.App()
#amp = Amp(verbose=15)
amp = Amp(protocol=".emulator",verbose=15)
with amp:
    Frame(amp).Show()
    app.MainLoop()


