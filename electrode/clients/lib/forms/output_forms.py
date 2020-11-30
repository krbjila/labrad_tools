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
from calibrations import *

from .gui_defaults_helpers import *

SEP = os.path.sep

class OutputForms(QtGui.QGroupBox):
	def __init__(self, calculator):
		super(OutputForms, self).__init__()
		self.calculator = calculator
		self.populate()

	def populate(self):
		self.setTitle("Outputs")

		self.layout = QtGui.QHBoxLayout()

		self.cMonitor = ChannelMonitor()
		self.pMonitor = ParameterMonitor()
		self.pMonitor.setCalculator(self.calculator)

		self.layout.addWidget(self.cMonitor)
		self.layout.addWidget(self.pMonitor)

		self.setLayout(self.layout)

	def update(self, vals, comp_shim):
		self.cMonitor.convertAndPopulate(vals)
		self.pMonitor.convertAndPopulate(self.compShimCorrection(vals, comp_shim))

	def compShimCorrection(self, values, comp_shim):
		vs = deepcopy(values)

		PlateSpan = vs['LP'] - vs['UP']
		bias = float(PlateSpan) / PLATE_SEPARATION * RODS_CORRECTION

		dEdx = comp_shim * bias / NORMALIZATION_FIELD

		vs['LW'] -= (-1.0)*dEdx
		vs['LE'] += (-1.0)*dEdx
		vs['UW'] += (-1.0)*dEdx
		vs['UE'] -= (-1.0)*dEdx

		return vs

class MonitorForm(QtGui.QGroupBox):

	def __init__(self, config):
		super(MonitorForm, self).__init__()
		self.config = config
		self.n_fields = len(self.config['long'])
		self.populate()

	def populate(self):
		self.layout = QtGui.QGridLayout()

		self.setTitle(self.config['title'])
		self.setCheckable(False)

		self.labels = []
		self.edits = []
		self.lookup = {}

		for i in range(len(self.config['short'])):
			shortname = self.config['short'][i]
			longname = self.config['long'][i]
			self.labels.append(QtGui.QLabel(str(longname)))
			self.edits.append(QtGui.QLineEdit())
			
			self.edits[i].setReadOnly(True)
			self.edits[i].setAlignment(QtCore.Qt.AlignRight)

			self.lookup[shortname] = i

			self.layout.addWidget(self.labels[i], i, 0, 1, 1)
			self.layout.addWidget(self.edits[i], i, 1, 1, 1)

		self.setLayout(self.layout)

	def getValues(self):
		self.values = {}
		for key,val in self.lookup.items():
			self.values[key] = float(self.edits[i].text())
		vals = deepcopy(self.values)
		return vals

class ChannelMonitor(MonitorForm):
	config = {
		'title' : 'DAC values (V)',
		'short' : FORM_FIELDS['i'],
		'long' : MONITOR_FIELDS['c'],
		'precisions' : FIELD_PRECISIONS['c']
	}
	def __init__(self):
		super(ChannelMonitor, self).__init__(self.config)

	def convertAndPopulate(self, Vs):
		DACVs = VsToDACs(Vs)

		for key, val in DACVs.items():
			index = self.lookup[key]
			precision = self.config['precisions'][index]
			self.edits[index].setText("{0:+0.{precision}f}".format(val, precision=precision))

class ParameterMonitor(MonitorForm):
	config = {
		'title' : 'Calculated params (from COMSOL)',
		'short' : FORM_FIELDS['p'],
		'long' : MONITOR_FIELDS['p'],
		'precisions' : FIELD_PRECISIONS['p']
	}

	def __init__(self):
		super(ParameterMonitor, self).__init__(self.config)

	def setCalculator(self, calculator):
		self.calculator = calculator

	def convertAndPopulate(self, Vs):
		v = self.calculator.parametersDump(Vs)

		for key, val in v.items():
			index = self.lookup[key]
			precision = self.config['precisions'][index]
			self.edits[index].setText("{0:+0.{precision}f}".format(val, precision=precision))
