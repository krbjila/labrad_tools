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

	def getCurrentItem(self):
		try:
			item = str(self.currentText()).split(':')[0]
			return int(item)
		except:
			return 0

	def setCurrentItem(self, setting_number):
		get_setting = lambda s: int(s.split(':')[0])
		for i in range(self.count()):
			try:
				s = get_setting(str(self.itemText(i)))
				if s == setting_number:
					self.setCurrentIndex(i)
					return i
			except Exception as e:
				print(e)
		self.setCurrentIndex(0)
		return 0