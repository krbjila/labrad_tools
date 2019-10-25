import json
import time
import numpy as np
import os
import sys

from PyQt4 import QtGui, QtCore, Qt
from PyQt4.QtCore import pyqtSignal 
from twisted.internet.defer import inlineCallbacks

sys.path.append('./widgets/')
from sequence_table import SequenceTable

SEP = os.path.sep

class SequenceSelect(QtGui.QWidget):
	def __init__(self):
		super(SequenceSelect, self).__init__()

		self.populate()

	def populate(self):
		self.layout = QtGui.QGridLayout()

		self.load_button = QtGui.QPushButton("Load")
		self.layout.addWidget(self.load_button, 0, 0, 1, 2)

		self.experiment_label = QtGui.QLabel("Experiment")
		self.layout.addWidget(self.experiment_label, 2, 0, 1, 1)

		self.experiment_edit = QtGui.QLineEdit("")
		self.experiment_edit.setReadOnly(True)
		self.layout.addWidget(self.experiment_edit, 2, 1, 1, 1)

		self.sequence_table = SequenceTable()
		self.layout.addWidget(self.sequence_table, 3, 0, 2, 4)

		self.setLayout(self.layout)