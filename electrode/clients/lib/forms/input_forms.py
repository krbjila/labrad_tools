from __future__ import absolute_import
import json
import time
import numpy as np
import os
import sys

from PyQt4 import QtGui, QtCore, Qt
from PyQt4.QtCore import pyqtSignal 
from twisted.internet.defer import inlineCallbacks

from copy import deepcopy

sys.path.append('../../client_tools')
from connection import connection
from widgets import SuperSpinBox

sys.path.append('../')
from calibrations import EFC

from .gui_defaults_helpers import *

SEP = os.path.sep

class InputForms(QtGui.QGroupBox):
	crossUpdated = pyqtSignal()

	def __init__(self):
		super(InputForms, self).__init__()
		self.populate()

	def populate(self):
		self.setTitle("Inputs")

		self.layout = QtGui.QHBoxLayout()

		self.nControl = NormalControl()
		self.iControl = IndependentControl()

		# Control like a button group -- exclusive selection
		self.nControl.clicked.connect(self.doButtonControl(0))
		self.iControl.clicked.connect(self.doButtonControl(1))
		self.nControl.setChecked(True)

		# Any return pressed signals
		self.nControl.anyEditingFinished.connect(self.crossUpdate)
		self.iControl.anyEditingFinished.connect(self.crossUpdate)

		# Watch for comp shim
		self.nControl.compShimChangedSignal.connect(self.compShimChanged)

		self.layout.addWidget(self.nControl)
		self.layout.addWidget(self.iControl)

		self.setLayout(self.layout)

	def compShimChanged(self, comp_shim):
		self.comp_shim = comp_shim
		self.iControl.updateCompShim(comp_shim)
		self.nControl.updateCompShim(comp_shim)
		self.crossUpdate(True)
		self.crossUpdate()

	def doButtonControl(self, ind):
		def buttonControl():
			self.crossUpdate()

			if ind == 0:
				self.nControl.setChecked(True)
				self.iControl.setChecked(False)
			else:
				self.nControl.setChecked(False)
				self.iControl.setChecked(True)
		return buttonControl

	def crossUpdate(self, flag=False):
		if flag:
			vals = self.iControl.getValues()[0]
			self.nControl.convertAndPopulate(vals)
		else:
			if self.nControl.isChecked():
				vals = self.nControl.getValues()[0]
				self.iControl.convertAndPopulate(vals)
			else:
				vals = self.iControl.getValues()[0]
				self.nControl.convertAndPopulate(vals)
			self.crossUpdated.emit()

class ControlForm(QtGui.QGroupBox):
	anyEditingFinished = pyqtSignal()

	def __init__(self, config):
		super(ControlForm, self).__init__()
		self.config = config
		self.n_fields = len(self.config['fields'])
		self.populate()
		self.initializeBoxes()

	def populate(self):
		self.layout = QtGui.QGridLayout()

		self.setTitle(self.config['title'])
		self.setCheckable(True)
		self.setChecked(False)

		self.labels = []
		self.edits = []
		self.lookup = {}

		for i in range(len(self.config['fields'])):
			f = self.config['fields'][i]
			self.labels.append(QtGui.QLabel(str(f)))
			self.edits.append(QtGui.QDoubleSpinBox())

			self.edits[i].setToolTip(self.config['tooltips'][str(f)])

			self.edits[i].editingFinished.connect(self.emitSignal)
			self.edits[i].setDecimals(self.config['precisions'][i])
			self.edits[i].setRange(self.config['min'][i], self.config['max'][i])
			self.edits[i].setSingleStep(self.config['step'][i])

			self.lookup[f] = i

			self.layout.addWidget(self.labels[i], i, 0, 1, 1)
			self.layout.addWidget(self.edits[i], i, 1, 1, 1)

		self.setLayout(self.layout)

	def emitSignal(self):
		self.anyEditingFinished.emit()

	def initializeBoxes(self):
		# If initial value data is invalid, don't use!
		if len(self.config['initialValues']) != self.n_fields:
			for i in self.edits:
				i.setValue(0)
		else:
			for i in range(self.n_fields):
				self.edits[i].setValue(float(self.config['initialValues'][i]))

	def _getValues(self):
		self.values = {}
		for i in range(len(self.edits)):
			key = str(self.labels[i].text())
			self.values[key] = float(self.edits[i].value())
		vals = deepcopy(self.values)
		return vals

class IndependentControl(ControlForm):
	config = {
		'title' : 'Independent control (V)',
		'fields' : FORM_FIELDS['i'],
		'initialValues' : [],
		'tooltips' : TOOLTIPS['i'],
		'precisions' : FIELD_PRECISIONS['i'],
		'min' : FIELD_MIN['i'],
		'max' : FIELD_MAX['i'],
		'step' : FIELD_STEP['i'],
	}
	def __init__(self):
		super(IndependentControl, self).__init__(self.config)
		self.comp_shim = 0

	def setValues(self, values):
		for i in range(len(self.edits)):
			key = str(self.labels[i].text())
			val = values[key]
			self.edits[i].setValue(val)

	def convertAndPopulate(self, NormalModes):
		Vs = NormalModesToVs(NormalModes)

		for key, val in Vs.items():
			index = self.lookup[key]
			self.edits[index].setValue(val)
	
	def updateCompShim(self, new_comp_shim):
		self.comp_shim = new_comp_shim

	def getValues(self):
		return (self._getValues(), self.comp_shim)

class NormalControl(ControlForm):
	compShimChangedSignal = pyqtSignal(float)

	config = {
		'title' : 'Normal modes',
		'fields' : FORM_FIELDS['n'],
		'initialValues' : [],
		'tooltips': TOOLTIPS['n'],
		'precisions' : FIELD_PRECISIONS['n'],
		'min' : FIELD_MIN['n'],
		'max' : FIELD_MAX['n'],
		'step' : FIELD_STEP['n'], 
	}
	def __init__(self):
		super(NormalControl, self).__init__(self.config)
		self.comp_shim = 0

		index = self.lookup['CompShim']
		self.edits[index].editingFinished.connect(self.compShimChanged)

	def compShimChanged(self):
		index = self.lookup['CompShim']
		val = self.edits[index].value()
		self.compShimChangedSignal.emit(val)

	def updateCompShim(self, comp_shim):
		self.comp_shim = comp_shim

	def convertAndPopulate(self, Vs):
		NormalModes = VsToNormalModes(Vs, self.comp_shim)

		for key, val in NormalModes.items():
			index = self.lookup[key]
			self.edits[index].setValue(val)

	def getValues(self):
		return (self._getValues(), self.comp_shim)
