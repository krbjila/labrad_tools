import json
import time
import numpy as np
import os
import sys

from PyQt4 import QtGui, QtCore, Qt
from PyQt4.QtCore import pyqtSignal 
from twisted.internet.defer import inlineCallbacks

sys.path.append('./widgets/')
from digital_form import DigitalForm
from analog_form import AnalogForm

SEP = os.path.sep

class ChannelSelect(QtGui.QWidget):
	def __init__(self, digital_channels, analog_channels):
		super(ChannelSelect, self).__init__()

		self.digital_channels = digital_channels
		self.analog_channels = analog_channels

		self.populate()

	def populate(self):
		self.layout = QtGui.QVBoxLayout()

		self.digital_form = DigitalForm(self.digital_channels)
		self.analog_form = AnalogForm(self.analog_channels)

		self.layout.addWidget(self.digital_form)
		self.layout.addWidget(self.analog_form)

		self.setLayout(self.layout)

	def setValues(self, values):
		pass