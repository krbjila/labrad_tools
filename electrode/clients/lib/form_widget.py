import json
import time
import numpy as np
import os
import sys

from PyQt4 import QtGui, QtCore, Qt
from PyQt4.QtCore import pyqtSignal 
from twisted.internet.defer import inlineCallbacks

from pathlib import Path
sys.path.append([str(i) for i in Path(__file__).parents if str(i).endswith("labrad_tools")][0])
from electrode.clients.lib.forms.input_forms import InputForms
from electrode.clients.lib.forms.output_forms import OutputForms
from electrode.clients.lib.forms.gui_defaults_helpers import *
from optimize_dialog import OptimizationDialog

from electrode.calibrations import *


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
	
