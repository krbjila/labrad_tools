from __future__ import absolute_import
import json
import time
import numpy as np
import os
import sys

from PyQt4 import QtGui, QtCore, Qt
from PyQt4.QtCore import pyqtSignal 
from twisted.internet.defer import inlineCallbacks

sys.path.append('./forms/')
from input_forms import InputForms
from output_forms import OutputForms
from gui_defaults_helpers import *
from .optimize_dialog import OptimizationDialog

sys.path.append('./../../')
from calibrations import *


CS_GEOMETRY = {
	'w': 200
}

class FormWidget(QtGui.QWidget):
	def __init__(self, calculator):
		super(FormWidget, self).__init__()
		self.calculator = calculator
		self.populate()

	def populate(self):
		self.layout = QtGui.QHBoxLayout()

		self.inputForms = InputForms()
		self.outputForms = OutputForms(self.calculator)
		self.inputForms.crossUpdated.connect(self.updateOutputForms)

		self.layout.addWidget(self.inputForms)
		self.layout.addWidget(self.outputForms)

		self.updateOutputForms()

		self.setLayout(self.layout)

	def getValues(self):
		return self.inputForms.iControl.getValues()

	def setValues(self, values, comp_shim):
		self.inputForms.iControl.setValues(values)
		self.inputForms.compShimChanged(comp_shim)
		self.updateOutputForms()

	def updateOutputForms(self):
		self.outputForms.update(*self.getValues())

	def setCompShim(self, comp_shim):
		self.inputForms.setCompShim(comp_shim)
	
