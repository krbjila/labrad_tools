import json
import time
import numpy as np
import os
import sys

from PyQt4 import QtGui, QtCore, Qt
from PyQt4.QtCore import pyqtSignal 
from twisted.internet.defer import inlineCallbacks

sys.path.append('./displays/')
from display_gui_elements import *

SEP = os.path.sep

class DisplayWidget(QtGui.QWidget):
	def __init__(self, calculator):
		super(DisplayWidget, self).__init__()
		self.calculator = calculator
		self.populate()

	def populate(self):
		self.layout = QtGui.QHBoxLayout()

		self.electrodeSchematic = ElectrodeSchematic()
		self.fieldSlicesWindow = FieldSlicesWindow(self.calculator)

		self.layout.addWidget(self.electrodeSchematic)
		self.layout.addWidget(self.fieldSlicesWindow)

		self.setLayout(self.layout)

	def setValues(self, values):
		self.values = values
		self.electrodeSchematic.redraw(values)
		self.fieldSlicesWindow.update(values)
