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

		# self.calculator = ECalculator(fit_coeffs_path)

		# self.setFixedWidth(WIDGET_GEOMETRY['w'])
		# self.setFixedHeight(WIDGET_GEOMETRY['h'])

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

		self.channel_select = ChannelSelect()

		self.digital_plot = DigitalPlot()
		self.analog_plot = AnalogPlot()


		# self.settings = SettingWidget()
		# self.forms = FormWidget(self.calculator)
		# # self.compShim = CompShimForm()
		# self.displays = DisplayWidget(self.calculator)

		# self.forms.inputForms.crossUpdated.connect(self.inputFormChanged)
		# self.settings.updateDescriptionSignal.connect(self.descriptionChanged)

		# self.settings.settingChangedSignal.connect(self.settingChanged)
		# self.settings.newSettingSignal.connect(self.newSettingAdded)
		# self.settings.saveSettingSignal.connect(self.saveSetting)
		# self.settings.settingDeletedSignal.connect(self.settingDeleted)
		# self.settings.refreshSignal.connect(self.refresh)

		# # self.compShim.compShimSignal.connect(self.setCompShim)

		# self.layout.addWidget(self.settings)
		# # self.layout.addWidget(self.compShim)
		# self.layout.addWidget(self.forms)
		# self.layout.addWidget(self.displays)

		font = QtGui.QFont()
		font.setPointSize(12)
		self.setFont(font)

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

		self.digital_channels = {k:v for k,v in self.channels.items() if v['channel_type'] == 'digital'}
		self.analog_channels = {k:v for k,v in self.channels.items() if (v['channel_type'] == 'analog' or v['channel_type'] == 'ad5791')}

		print self.analog_channels.keys()



if __name__ == '__main__':
    a = QtGui.QApplication([])

    import qt4reactor 
    qt4reactor.install()
    from twisted.internet import reactor
    widget = VisualizerWindow(reactor)

    widget.show()
    reactor.run()