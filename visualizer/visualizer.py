import json
import time
import numpy as np
import os
import sys

from PyQt4 import QtGui, QtCore, Qt
from PyQt4.QtCore import pyqtSignal 
from twisted.internet.defer import inlineCallbacks

sys.path.append('./lib/')
sys.path.append('./lib/widgets')
from channel_select import ChannelSelect
from digital_plot import DigitalPlot
from analog_plot import AnalogPlot

# sys.path.append('./lib/')
# sys.path.append('./lib/forms')
# sys.path.append('./lib/settings')
# sys.path.append('./lib/displays')
# sys.path.append('./lib/efield')

# from form_widget import FormWidget
# from setting_widget import SettingWidget
# from display_widget import DisplayWidget 
# from calculator import ECalculator

# from helpers import json_loads_byteified
# from gui_defaults_helpers import DACsToVs, VsToDACs

sys.path.append('../client_tools')
from connection import connection
# SERVERNAME = "electrode"

# SEP = os.path.sep
# fit_coeffs_path = './lib/efield/comsol/data/fit_coeffs.json'

# WIDGET_GEOMETRY = {
# 	'w' : 1600,
# 	'h' : 800
# }

class ConfigWrapper(object):
    def __init__(self, **config_entries):
        self.__dict__.update(config_entries)

class VisualizerWindow(QtGui.QWidget):
	def __init__(self, reactor, config_path='./config.json'):

		super(VisualizerWindow, self).__init__()
		self.reactor = reactor
		self.load_config(config_path)
		self.channels = {}
		self.initialize()

	def load_config(self, path=None):
		if path is not None:
			self.config_path = path
		with open(self.config_path, 'r') as infile:
			config = json.load(infile)
			self.config = ConfigWrapper(**config)
			for key, value in config.items():
				setattr(self, key, value)


	def populate(self):
		self.setWindowTitle("Sequence visualizer")
		self.layout = QtGui.QVBoxLayout()

		self.channel_select = ChannelSelect(self.digital_channels, self.analog_channels)

		self.channel_scroll = QtGui.QScrollArea()
		self.channel_scroll.setWidget(self.channel_select)

		# self.digital_plot = DigitalPlot()
		# self.analog_plot = AnalogPlot()

		self.channel_scroll.setHorizontalScrollBarPolicy(1)
		self.channel_scroll.setVerticalScrollBarPolicy(2)
		self.channel_scroll.setFrameShape(0)

		font = QtGui.QFont()
		font.setPointSize(12)
		self.setFont(font)

		self.layout.addWidget(self.channel_scroll)

		self.setLayout(self.layout)

	@inlineCallbacks
	def initialize(self):
		yield self.connect()
		yield self.getChannels()
		yield self.populate()


	@inlineCallbacks
	def connect(self):
		self.cxn = connection()  
		yield self.cxn.connect()

		self.context = yield self.cxn.context()
		self.sequencer = yield self.cxn.get_server(self.sequencer_servername)
		self.conductor = yield self.cxn.get_server(self.conductor_servername)

	@inlineCallbacks
	def getChannels(self):
		s = yield self.sequencer.get_channels()
		self.channels = json.loads(s)

		self.digital_channels = {}
		self.analog_channels = {}

		# Get channels by board
		for k, v in self.channels.items():
			board = v['loc'][0]

			if v['channel_type'] == 'digital':
				if not board in self.digital_channels:
					self.digital_channels[board] = {}
				self.digital_channels[board][k] = v
			else:
				if not board in self.analog_channels:
					self.analog_channels[board] = {}
				self.analog_channels[board][k] = v



if __name__ == '__main__':
    a = QtGui.QApplication([])

    import qt4reactor 
    qt4reactor.install()
    from twisted.internet import reactor
    widget = VisualizerWindow(reactor)

    widget.show()
    reactor.run()