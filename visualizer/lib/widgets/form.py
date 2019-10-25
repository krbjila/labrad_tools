import json
import time
import numpy as np
import os
import sys

from PyQt4 import QtGui, QtCore, Qt
from PyQt4.QtCore import pyqtSignal 
from twisted.internet.defer import inlineCallbacks

from channel_widgets import *

SEP = os.path.sep

class Form(QtGui.QWidget):
	any_changed = pyqtSignal()

	def __init__(self, form_type, channels):
		super(Form, self).__init__()
		self.form_type = form_type
		self.channels = channels
		self.populate()

	def populate(self):
		self.layout = QtGui.QVBoxLayout()
		self.boards = {}

		for board in sorted(self.channels.keys()):
			b = SequencerBoard(board, self.channels[board], self.form_type)
			b.any_changed.connect(self.changed)
			self.boards[board] = b
			self.layout.addWidget(b)

		self.setLayout(self.layout)

	def minimizeAll(self):
		for b in self.boards.values():
			if b.toggle_button.isChecked():
				b.toggle_button.click()

	def uncheckAll(self):
		for b in self.boards.values():
			b.uncheckAll()

	def getCheckedChannels(self):
		checked = []
		for b in self.boards.values():
			checked += b.getCheckedChannels()
		return checked

	def changed(self):
		self.any_changed.emit()
