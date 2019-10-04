import json
import time
import numpy as np
import os
import sys

from PyQt4 import QtGui, QtCore, Qt
from PyQt4.QtCore import pyqtSignal 
from twisted.internet.defer import inlineCallbacks

SEP = os.path.sep

class SettingControl(QtGui.QComboBox):
	cleanedCurrentIndexChanged = pyqtSignal()

	def __init__(self):
		super(SettingControl, self).__init__()
	
	def setSettings(self, settings):
		self.settings = settings
		self.populate()

	def populate(self):
		self.clear()

		for i in range(len(self.settings)):
			preset = self.settings[i]
			self.addItem("")
			self.setItem(i, preset)
		self.addItem("New...")

	def setItem(self, item, preset):
		self.setItemText(item, "{}: {}".format(int(preset['id']), preset['description']))		