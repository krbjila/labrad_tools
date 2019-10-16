import json
import time
import numpy as np
import os
import sys

from PyQt4 import QtGui, QtCore, Qt
from PyQt4.QtCore import pyqtSignal 
from twisted.internet.defer import inlineCallbacks

# sys.path.append('./displays/')
# from display_gui_elements import *

SEP = os.path.sep

class SequencerBoard(QtGui.QGroupBox):
	def __init__(self, channels, board_type):
		super(SequencerBoard, self).__init__()
		self.channels = channels
		self.type = board_type

		self.populate()

	def populate(self):
		self.layout = QtGui.QVBoxLayout()

		self.channel_widgets = []

		for k in sorted(self.channels.keys(), key=lambda k: k.split('@')[1]):
			c = SequencerChannel(k.split('@')[1], self.channels[k], self.type)
			self.channel_widgets.append(c)
			self.layout.addWidget(c)

		self.setLayout(self.layout)

class SequencerChannel(QtGui.QWidget):
	def __init__(self, channel_name, channel_data, channel_type):
		super(SequencerChannel, self).__init__()
		self.name = channel_name
		self.type = channel_type

		for key, val in channel_data.items():
			setattr(self, key, val)

		self.populate()

	def populate(self):
		self.layout = QtGui.QHBoxLayout()

		self.checkbox = QtGui.QCheckBox()
		if self.type == 'digital':
			self.label = QtGui.QLabel(self.loc + ': ' + self.name)
		else:
			self.label = QtGui.QLabel(self.name)

		self.layout.addWidget(self.checkbox)
		self.layout.addWidget(self.label)

		self.setLayout(self.layout)