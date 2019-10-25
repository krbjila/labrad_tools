import json
import time
import numpy as np
import os
import sys

from PyQt4 import QtGui, QtCore, Qt
from PyQt4.QtCore import pyqtSignal 
from twisted.internet.defer import inlineCallbacks

sys.path.append('./widgets/')
from form import Form

SEP = os.path.sep

class ChannelSelect(QtGui.QWidget):
	any_changed = pyqtSignal()

	def __init__(self, digital_channels, analog_channels):
		super(ChannelSelect, self).__init__()

		self.digital_channels = digital_channels
		self.analog_channels = analog_channels

		self.populate()

	def populate(self):
		self.layout = QtGui.QVBoxLayout()

		self.minimize_button = QtGui.QPushButton("Minimize all")
		self.minimize_button.clicked.connect(self.minimize)

		self.uncheck_button = QtGui.QPushButton("Uncheck all")
		self.uncheck_button.clicked.connect(self.uncheckAll)

		self.digital_form = Form('digital', self.digital_channels)
		self.digital_form.any_changed.connect(self.changed)

		self.analog_form = Form('analog', self.analog_channels)
		self.analog_form.any_changed.connect(self.changed)

		self.layout.addWidget(self.minimize_button)
		self.layout.addWidget(self.uncheck_button)
		self.layout.addWidget(self.digital_form)
		self.layout.addWidget(self.analog_form)

		self.layout.addStretch()

		self.setLayout(self.layout)

	def changed(self):
		self.any_changed.emit()

	def getCheckedChannels(self):
		checked = self.digital_form.getCheckedChannels() + self.analog_form.getCheckedChannels()
		return checked

	def uncheckAll(self):
		self.digital_form.uncheckAll()
		self.analog_form.uncheckAll()
		self.minimize()
		self.changed()

	def minimize(self):
		self.digital_form.minimizeAll()
		self.analog_form.minimizeAll()

	