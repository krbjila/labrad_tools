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

class AnalogForm(QtGui.QWidget):
	def __init__(self):
		super(AnalogForm, self).__init__()
		self.populate()

	def populate(self):
		self.layout = QtGui.QHBoxLayout()

		self.setLayout(self.layout)

	def setValues(self, values):
		pass