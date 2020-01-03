import json
import time
import numpy as np
import os
import sys

from PyQt4 import QtGui, QtCore, Qt
from PyQt4.QtCore import pyqtSignal 
from twisted.internet.defer import inlineCallbacks

sys.path.append('./widgets/')
from plot_widgets import *

SEP = os.path.sep

class Plot(QtGui.QWidget):
	export_csv = pyqtSignal()
	export_json = pyqtSignal()

	def __init__(self, digital_channels, analog_channels, timing_channel):
		super(Plot, self).__init__()

		self.digital_channels = digital_channels
		self.analog_channels = analog_channels
		self.timing_channel = timing_channel

		self.populate()

	def populate(self):
		self.layout = QtGui.QVBoxLayout()

		self.imageWindow = ImageWindow(self.digital_channels, self.analog_channels, self.timing_channel)
		self.selector = RegionSelector()
		self.selector.region_changed.connect(self.setRegion)
		self.selector.autoscale_changed.connect(self.setAutoscale)

		self.selector.export_csv_button.clicked.connect(self.exportCSV)
		self.selector.export_json_button.clicked.connect(self.exportJSON)

		self.scroll = QtGui.QScrollArea()
		self.scroll.setWidget(self.imageWindow)
		self.scroll.setWidgetResizable(True)

		self.scroll.setHorizontalScrollBarPolicy(2)
		self.scroll.setVerticalScrollBarPolicy(1)
		self.scroll.setFrameShape(0)

		self.layout.addWidget(self.selector)
		self.layout.addWidget(self.scroll)
		self.setLayout(self.layout)

	def exportCSV(self):
		self.export_csv.emit()

	def exportJSON(self):
		self.export_json.emit()

	def setRegion(self, start, stop):
		self.imageWindow.setRegion(start, stop)

	def setAutoscale(self, autoscale):
		self.imageWindow.setAutoscale(autoscale)

	def setModules(self, sequence_list):
		self.selector.setModules(sequence_list)

	def setSequence(self, sequence, times):
		self.sequence = sequence
		self.times = times

		self.imageWindow.setSequence(sequence)
		self.selector.setTimes(times)

	def setActiveChannels(self, channels):
		self.imageWindow.setActiveChannels(channels)
