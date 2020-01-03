import json
import time
import numpy as np
import os
import sys

from datetime import date, timedelta

from PyQt4 import QtGui, QtCore, Qt
from PyQt4.QtCore import pyqtSignal 
from twisted.internet.defer import inlineCallbacks

sys.path.append('./lib/')
sys.path.append('./lib/widgets')
from channel_select import ChannelSelect
from sequence_select import SequenceSelect
from plot import Plot

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

class Visualizer(QtGui.QWidget):
	def __init__(self, reactor, config_path='./config.json'):
		super(Visualizer, self).__init__()
		self.reactor = reactor
		self.config_path = config_path
		self.load_config(config_path)

		self.populate()
		self.resize(self.window_width, self.window_height)

	def load_config(self, path=None):
		if path is not None:
			self.config_path = path
		with open(self.config_path, 'r') as infile:
			config = json.load(infile)
			self.config = ConfigWrapper(**config)
			for key, value in config.items():
				setattr(self, key, value)

	def populate(self):
		self.layout = QtGui.QHBoxLayout()

		self.visualizer = VisualizerWidget(self.reactor, self.config_path)

		self.scroll = QtGui.QScrollArea()
		self.scroll.setWidget(self.visualizer)
		self.scroll.setWidgetResizable(True)
		self.scroll.setHorizontalScrollBarPolicy(1)
		self.scroll.setVerticalScrollBarPolicy(2)
		self.scroll.setFrameShape(0)

		self.layout.addWidget(self.scroll)
		self.setLayout(self.layout)


class VisualizerWidget(QtGui.QWidget):
	def __init__(self, reactor, config_path='./config.json'):

		super(VisualizerWidget, self).__init__()
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
		self.layout = QtGui.QGridLayout()

		self.sequence_select_label = QtGui.QLabel("Sequence selection:")
		self.sequence_select = SequenceSelect()
		self.sequence_select.setFixedWidth(self.module_width + self.date_width)
		self.sequence_select.sequence_table.setColumnWidth(0, self.module_width)
		self.sequence_select.sequence_table.setColumnWidth(1, self.date_width)
		self.sequence_select.load_button.clicked.connect(self.load)

		self.sequence_scroll = QtGui.QScrollArea()
		self.sequence_scroll.setWidget(self.sequence_select)
		self.sequence_scroll.setWidgetResizable(True)
		self.sequence_scroll.setFixedWidth(self.module_width + self.date_width)
		self.sequence_scroll.setFixedHeight(self.upperscrolls_height)

		self.sequence_scroll.setHorizontalScrollBarPolicy(1)
		self.sequence_scroll.setVerticalScrollBarPolicy(2)
		self.sequence_scroll.setFrameShape(0)

		self.channel_select_label = QtGui.QLabel("Channels to display:")
		self.channel_select = ChannelSelect(self.digital_channels, self.analog_channels)
		self.channel_select.any_changed.connect(self.channelsChanged)

		for b in self.channel_select.digital_form.boards.values():
			for c in b.channel_widgets:
				c.label.setFixedSize(self.channellabel_width, self.checkbox_size)
				c.checkbox.setFixedSize(self.checkbox_size, self.checkbox_size)

		for b in self.channel_select.analog_form.boards.values():
			for c in b.channel_widgets:
				c.label.setFixedSize(self.channellabel_width, self.checkbox_size)
				c.checkbox.setFixedSize(self.checkbox_size, self.checkbox_size)

		self.channel_scroll = QtGui.QScrollArea()
		self.channel_scroll.setWidget(self.channel_select)
		self.channel_scroll.setWidgetResizable(True)
		self.channel_scroll.setFixedWidth(self.channellabel_width + self.checkbox_size)
		self.channel_scroll.setFixedHeight(self.upperscrolls_height)

		self.channel_scroll.setHorizontalScrollBarPolicy(1)
		self.channel_scroll.setVerticalScrollBarPolicy(2)
		self.channel_scroll.setFrameShape(0)

		#####################################

		self.plot_label = QtGui.QLabel("Plotter:")
		self.plot = Plot(self.digital_channels, self.analog_channels, self.timing_channel)
		self.plot.selector.setFixedSize(*self.selector_dim)
		self.plot.scroll.setFixedSize(*self.plot_dim)
		self.plot.export_csv.connect(self.exportCSV)
		self.plot.export_json.connect(self.exportJSON)

		font = QtGui.QFont()
		font.setPointSize(10)
		self.setFont(font)

		headerFont = QtGui.QFont()
		headerFont.setPointSize(16)
		headerFont.setBold(True)
		self.sequence_select_label.setFont(headerFont)
		self.channel_select_label.setFont(headerFont)
		self.plot_label.setFont(headerFont)

		self.layout.addWidget(self.sequence_select_label, 0, 0, 1, 1)
		self.layout.addWidget(self.sequence_scroll, 1, 0, 1, 1)

		self.layout.addWidget(self.channel_select_label, 0, 1, 1, 1)
		self.layout.addWidget(self.channel_scroll, 1, 1, 1, 1)

		self.layout.addWidget(self.plot_label, 5, 0, 1, 1)
		self.layout.addWidget(self.plot, 6, 0, 1, 4)

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

	# Load an experiment file
	def load(self):
		timestr = time.strftime(self.time_format)
		directory = self.experiment_directory.format(timestr)
		if os.path.exists(directory):
			directory = directory
		else:
			directory = self.experiment_directory.split('{}')[0]
		filepath = QtGui.QFileDialog().getOpenFileName(directory=directory)
		if filepath:
			self.sequence_select.experiment_edit.setText(filepath)
			with open(filepath) as f:
				r = json.load(f)
			# This is the list of modules
			sequence_list = r["parameter_values"]["sequencer"]["sequence"]
			self.loadExperiment(sequence_list)

	# Handle list of modules
	def loadExperiment(self, sequence_list):
		# Get the date of each module
		dated_sequence = self.getVersion(sequence_list)
		self.sequence_select.sequence_table.update(dated_sequence)
		self.dated_sequence = dated_sequence

		# Set plot's combobox with modules
		self.plot.setModules(sequence_list)

		# Get actual sequences by channel, metadata
		s_array = []
		m_array = []
		for m, d in self.dated_sequence:
			directory = self.sequence_directory.format(d)
			with open(directory + m) as f:
				data = json.load(f)
				s_array.append(data['sequence'])
				m_array.append(data['meta'])

		# Combine sequences
		# Get sequence durations
		self.sequence = {}
		self.times = []
		for s in s_array:
			t = 0
			for x in s[self.timing_channel]:
				t += x['dt']
			self.times.append(t)

			for key,val in s.items():
				if self.sequence.has_key(key):
					self.sequence[key] += val
				else:
					self.sequence[key] = val

		# Plot the sequence
		self.plot.setSequence(self.sequence, self.times)

	# Get versions of sequences
	def getVersion(self, sequence_list):
		dated_sequence = []

		for module in sequence_list:
			timestr = time.strftime(self.time_format)
			directory = self.sequence_directory.format(timestr)
			filename = directory + module

			if os.path.exists(filename):
				dated_sequence.append((module, timestr))
			if not os.path.exists(filename):
				found = False
				for i in range(365):
					day = date.today() - timedelta(i)
					timestr = day.strftime(self.time_format)
					path = self.sequence_directory.format(timestr) + module
					if os.path.exists(path):
						dated_sequence.append((module,timestr))
						found = True
						break
				if not found:
					dated_sequence.append((module, 'invalid'))
		return dated_sequence

	def channelsChanged(self):
		active_channels = self.channel_select.getCheckedChannels()
		self.plot.setActiveChannels(active_channels)

	def exportCSV(self):
		filepath = QtGui.QFileDialog.getSaveFileName(directory=self.home_directory, filter="CSV Files (*.csv)")
		
		if filepath:
			d = self.plot.imageWindow.getPlottable()

			x = []
			for k, v in sorted(d['digital'].items(), key=lambda k: k[0].split('@')[-1]):
				v = np.array(v)

				if len(x) == 0:
					x = v
				else:
					hx = np.shape(x)[0]
					hv = np.shape(v)[0]

					if hx > hv:
						v = np.pad(v, ((0,hx-hv),(0,0)), mode='edge')
					elif hx < hv:
						x = np.pad(x, ((0,hv-hx),(0,0)), mode='edge')
					x = np.hstack((x, np.array(v)))

			for k, v in sorted(d['analog'].items(), key=lambda k: k[0].split('@')[-1]):
				v = np.array(v)

				if len(x) == 0:
					x = v
				else:
					hx = np.shape(x)[0]
					hv = np.shape(v)[0]

					if hx > hv:
						v = np.pad(v, ((0,hx-hv),(0,0)), mode='edge')
					elif hx < hv:
						x = np.pad(x, ((0,hv-hx),(0,0)), mode='edge')
					x = np.hstack((x, np.array(v)))

			with open(filepath, 'w') as f:
				np.savetxt(f, x, delimiter=',')

	def exportJSON(self):
		filepath = QtGui.QFileDialog.getSaveFileName(directory=self.home_directory, filter="JSON Files (*.json)")
		
		if filepath:
			d = self.plot.imageWindow.getPlottable()

			for kk, vv in d.items():
				x = {}
				for k, v in vv.items():
					v = np.array(v)
					x.update({k : {'t': list(v[:,0]), 'v': list(v[:,1])}})
				d.update({kk: x})

			with open(filepath, 'w') as f:
				json.dump(d, f, indent=4, sort_keys=True)

if __name__ == '__main__':
    a = QtGui.QApplication([])

    import qt4reactor 
    qt4reactor.install()
    from twisted.internet import reactor
    widget = Visualizer(reactor)

    widget.show()
    reactor.run()