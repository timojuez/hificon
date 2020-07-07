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
		wx.Frame.__init__ ( self, parent, id = wx.ID_ANY, title = wx.EmptyString, pos = wx.DefaultPosition, size = wx.Size( 101,234 ), style = wx.FRAME_NO_TASKBAR|wx.STAY_ON_TOP|wx.BORDER_NONE )

		self.SetSizeHints( wx.DefaultSize, wx.DefaultSize )


	def __del__( self ):
		pass


###########################################################################
## Class GaugeNotification
###########################################################################

class GaugeNotification ( wx.Panel ):

	def __init__( self, parent, id = wx.ID_ANY, pos = wx.DefaultPosition, size = wx.Size( -1,-1 ), style = wx.BORDER_NONE, name = wx.EmptyString ):
		wx.Panel.__init__ ( self, parent, id = id, pos = pos, size = size, style = style, name = name )

		self.SetForegroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_INFOTEXT ) )
		self.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_ACTIVECAPTION ) )

		border = wx.BoxSizer( wx.VERTICAL )

		vbox_outer = wx.BoxSizer( wx.VERTICAL )

		self.title = wx.StaticText( self, wx.ID_ANY, u"MyLabel", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.title.Wrap( -1 )

		self.title.SetFont( wx.Font( wx.NORMAL_FONT.GetPointSize(), wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD, False, wx.EmptyString ) )
		self.title.SetForegroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_CAPTIONTEXT ) )

		vbox_outer.Add( self.title, 0, wx.ALIGN_CENTER_HORIZONTAL|wx.ALL, 5 )

		gauge = wx.BoxSizer( wx.VERTICAL )

		self.empty = wx.StaticLine( self, wx.ID_ANY, wx.DefaultPosition, wx.Size( 20,30 ), wx.LI_VERTICAL )
		self.empty.SetForegroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_CAPTIONTEXT ) )
		self.empty.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_WINDOWFRAME ) )

		gauge.Add( self.empty, 1, wx.ALL|wx.ALIGN_CENTER_HORIZONTAL, 0 )

		self.progress = wx.StaticText( self, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.Size( 20,50 ), 0 )
		self.progress.Wrap( -1 )

		self.progress.SetForegroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_HIGHLIGHT ) )
		self.progress.SetBackgroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_HIGHLIGHT ) )

		gauge.Add( self.progress, 0, wx.ALL|wx.ALIGN_CENTER_HORIZONTAL, 0 )


		vbox_outer.Add( gauge, 1, wx.ALIGN_CENTER, 5 )

		self.subtitle = wx.StaticText( self, wx.ID_ANY, u"MyLabel", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.subtitle.Wrap( -1 )

		self.subtitle.SetFont( wx.Font( wx.NORMAL_FONT.GetPointSize(), wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD, False, wx.EmptyString ) )
		self.subtitle.SetForegroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_CAPTIONTEXT ) )

		vbox_outer.Add( self.subtitle, 0, wx.ALL|wx.ALIGN_CENTER_HORIZONTAL, 5 )


		border.Add( vbox_outer, 1, wx.ALIGN_CENTER_HORIZONTAL|wx.ALL, 10 )


		self.SetSizer( border )
		self.Layout()
		border.Fit( self )

	def __del__( self ):
		pass


