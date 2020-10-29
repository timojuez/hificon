# -*- coding: utf-8 -*-

###########################################################################
## Python code generated with wxFormBuilder (version 3.9.0 Jul  7 2020)
## http://www.wxformbuilder.org/
##
## PLEASE DO *NOT* EDIT THIS FILE!
###########################################################################

import wx
import wx.xrc

###########################################################################
## Class Frame
###########################################################################

class Frame ( wx.Frame ):

	def __init__( self, parent ):
		wx.Frame.__init__ ( self, parent, id = wx.ID_ANY, title = u"%(name)s Control Menu – %(amp)s", pos = wx.DefaultPosition, size = wx.Size( 436,434 ), style = wx.DEFAULT_FRAME_STYLE|wx.TAB_TRAVERSAL )

		self.SetSizeHints( wx.DefaultSize, wx.DefaultSize )

		bSizer4 = wx.BoxSizer( wx.VERTICAL )

		self.scrolledWindow = wx.ScrolledWindow( self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.HSCROLL|wx.VSCROLL )
		self.scrolledWindow.SetScrollRate( 5, 5 )
		bSizer10 = wx.BoxSizer( wx.VERTICAL )

		self.top_panel = wx.Panel( self.scrolledWindow, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.TAB_TRAVERSAL|wx.TRANSPARENT_WINDOW )
		bSizer19 = wx.BoxSizer( wx.VERTICAL )


		self.top_panel.SetSizer( bSizer19 )
		self.top_panel.Layout()
		bSizer19.Fit( self.top_panel )
		bSizer10.Add( self.top_panel, 0, wx.ALL|wx.EXPAND, 5 )

		self.content = wx.Panel( self.scrolledWindow, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.TAB_TRAVERSAL|wx.TRANSPARENT_WINDOW )
		bSizer192 = wx.BoxSizer( wx.VERTICAL )

		self.m_collapsiblePane1 = wx.CollapsiblePane( self.content, wx.ID_ANY, u"expand", wx.DefaultPosition, wx.Size( -1,-1 ), wx.CP_DEFAULT_STYLE|wx.CP_NO_TLW_RESIZE|wx.VSCROLL )
		self.m_collapsiblePane1.Collapse( True )

		self.m_collapsiblePane1.Hide()

		box = wx.BoxSizer( wx.VERTICAL )

		bSizer11 = wx.BoxSizer( wx.VERTICAL )

		boolFeature = wx.BoxSizer( wx.HORIZONTAL )

		self.m_staticText2 = wx.StaticText( self.m_collapsiblePane1.GetPane(), wx.ID_ANY, u"MyLabel", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_staticText2.Wrap( -1 )

		self.m_staticText2.SetForegroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_WINDOWTEXT ) )

		boolFeature.Add( self.m_staticText2, 0, wx.ALL, 5 )

		self.m_checkBox1 = wx.CheckBox( self.m_collapsiblePane1.GetPane(), wx.ID_ANY, u"Active", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_checkBox1.SetValue(True)
		boolFeature.Add( self.m_checkBox1, 1, wx.ALL, 5 )

		self.m_checkBox3 = wx.CheckBox( self.m_collapsiblePane1.GetPane(), wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.DefaultSize, 0 )
		boolFeature.Add( self.m_checkBox3, 0, wx.ALL, 5 )


		bSizer11.Add( boolFeature, 0, wx.EXPAND, 5 )

		selectFeature = wx.BoxSizer( wx.HORIZONTAL )

		self.m_staticText3 = wx.StaticText( self.m_collapsiblePane1.GetPane(), wx.ID_ANY, u"MyLabel", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_staticText3.Wrap( -1 )

		selectFeature.Add( self.m_staticText3, 0, wx.ALL, 5 )

		m_choice1Choices = [ u"ab", u"daf", u"cd" ]
		self.m_choice1 = wx.Choice( self.m_collapsiblePane1.GetPane(), wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, m_choice1Choices, 0 )
		self.m_choice1.SetSelection( 2 )
		selectFeature.Add( self.m_choice1, 1, wx.ALL, 5 )

		self.m_checkBox4 = wx.CheckBox( self.m_collapsiblePane1.GetPane(), wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.DefaultSize, 0 )
		selectFeature.Add( self.m_checkBox4, 0, wx.ALL, 5 )


		bSizer11.Add( selectFeature, 0, wx.EXPAND, 5 )

		self.m_panel2 = wx.Panel( self.m_collapsiblePane1.GetPane(), wx.ID_ANY, wx.DefaultPosition, wx.Size( -1,-1 ), wx.TAB_TRAVERSAL )
		self.m_panel2.SetForegroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_WINDOW ) )
		self.m_panel2.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_WINDOW ) )

		numericFeature = wx.BoxSizer( wx.HORIZONTAL )

		self.m_staticText5 = wx.StaticText( self.m_panel2, wx.ID_ANY, u"MyLabel asdf sadf sfwe fewf ", wx.DefaultPosition, wx.Size( 100,-1 ), wx.ST_ELLIPSIZE_MIDDLE )
		self.m_staticText5.Wrap( 2 )

		numericFeature.Add( self.m_staticText5, 0, wx.ALL, 5 )

		self.m_slider1 = wx.Slider( self.m_panel2, wx.ID_ANY, 0, -100, 100, wx.DefaultPosition, wx.DefaultSize, wx.SL_AUTOTICKS|wx.SL_HORIZONTAL )
		numericFeature.Add( self.m_slider1, 1, wx.ALL, 5 )

		self.m_staticText4 = wx.StaticText( self.m_panel2, wx.ID_ANY, u"0", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_staticText4.Wrap( -1 )

		numericFeature.Add( self.m_staticText4, 0, wx.ALL, 5 )

		self.m_checkBox2 = wx.CheckBox( self.m_panel2, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_checkBox2.SetToolTip( u"highlight" )

		numericFeature.Add( self.m_checkBox2, 0, wx.ALL, 5 )


		self.m_panel2.SetSizer( numericFeature )
		self.m_panel2.Layout()
		numericFeature.Fit( self.m_panel2 )
		bSizer11.Add( self.m_panel2, 1, wx.EXPAND |wx.ALL, 5 )


		box.Add( bSizer11, 1, wx.EXPAND, 5 )


		self.m_collapsiblePane1.GetPane().SetSizer( box )
		self.m_collapsiblePane1.GetPane().Layout()
		box.Fit( self.m_collapsiblePane1.GetPane() )
		bSizer192.Add( self.m_collapsiblePane1, 0, wx.ALL|wx.EXPAND, 5 )


		self.content.SetSizer( bSizer192 )
		self.content.Layout()
		bSizer192.Fit( self.content )
		bSizer10.Add( self.content, 0, wx.EXPAND |wx.ALL, 5 )

		self.buttom_panel = wx.Panel( self.scrolledWindow, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.TAB_TRAVERSAL|wx.TRANSPARENT_WINDOW )
		bSizer191 = wx.BoxSizer( wx.VERTICAL )


		self.buttom_panel.SetSizer( bSizer191 )
		self.buttom_panel.Layout()
		bSizer191.Fit( self.buttom_panel )
		bSizer10.Add( self.buttom_panel, 0, wx.EXPAND |wx.ALL, 5 )


		self.scrolledWindow.SetSizer( bSizer10 )
		self.scrolledWindow.Layout()
		bSizer10.Fit( self.scrolledWindow )
		bSizer4.Add( self.scrolledWindow, 1, wx.EXPAND |wx.ALL, 5 )


		self.SetSizer( bSizer4 )
		self.Layout()

		self.Centre( wx.BOTH )

		# Connect Events
		self.m_checkBox1.Bind( wx.EVT_CHECKBOX, self.m_checkBox1OnCheckBox )
		self.m_choice1.Bind( wx.EVT_CHOICE, self.m_choice1OnChoice )
		self.m_slider1.Bind( wx.EVT_SCROLL, self.m_slider1OnScroll )
		self.m_checkBox2.Bind( wx.EVT_CHECKBOX, self.m_checkBox2OnCheckBox )

	def __del__( self ):
		pass


	# Virtual event handlers, overide them in your derived class
	def m_checkBox1OnCheckBox( self, event ):
		event.Skip()

	def m_choice1OnChoice( self, event ):
		event.Skip()

	def m_slider1OnScroll( self, event ):
		event.Skip()

	def m_checkBox2OnCheckBox( self, event ):
		event.Skip()


