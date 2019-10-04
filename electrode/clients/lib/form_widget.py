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
		self.outputForms.update(self.getValues()[0])

	def setCompShim(self, comp_shim):
		self.inputForms.setCompShim(comp_shim)
		
# class CompShimForm(QtGui.QWidget):
# 	config = {
# 		'title' : 'Comp shim (scaled V)',
# 		'tooltips' : TOOLTIPS['cs'],
# 		'precisions' : FIELD_PRECISIONS['cs'],
# 		'min' : FIELD_MIN['cs'],
# 		'max' : FIELD_MAX['cs'],
# 		'step' : FIELD_STEP['cs']
# 	}

# 	compShimSignal = pyqtSignal(float)

# 	def __init__(self):
# 		super(CompShimForm, self).__init__()
# 		self.populate()
# 		self.setFixedWidth(CS_GEOMETRY['w'])

# 	def populate(self):
# 		self.layout = QtGui.QVBoxLayout()

# 		self.label = QtGui.QLabel(self.config['title'])

# 		self.edit = QtGui.QDoubleSpinBox()
# 		self.edit.setValue(COMP_SHIM_DEFAULT)
# 		self.edit.setToolTip(self.config['tooltips']['cs'])
# 		self.edit.editingFinished.connect(self.emitSignal)
# 		self.edit.setDecimals(self.config['precisions'][0])
# 		self.edit.setRange(self.config['min'][0], self.config['max'][0])
# 		self.edit.setSingleStep(self.config['step'][0])

# 		self.layout.addWidget(self.label)
# 		self.layout.addWidget(self.edit)
# 		self.setLayout(self.layout)

# 	def getCompShim(self):
# 		return self.edit.value()

# 	def emitSignal(self):
# 		self.compShimSignal.emit(self.getCompShim())
