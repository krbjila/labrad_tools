from __future__ import print_function
import json
import time
import numpy as np
import os
import sys

from copy import deepcopy

import timeit

from PyQt4 import QtGui, QtCore, Qt
from PyQt4.QtCore import pyqtSignal 
from twisted.internet.defer import inlineCallbacks

from scipy.optimize import least_squares

sys.path.append('../../')
sys.path.append('../efield/')

from calibrations import *
from calculator import *

sys.path.append('./forms/')
from gui_defaults_helpers import *

OPT_FIELDS = ['Bias', 'Angle', 'dEdx', 'dEdy', 'nux', 'nuy']
OPT_LONG = ['Bias (V/cm)', 'Angle from vertical (deg)', 'd|E|/dx (V/cm^2)', 'd|E|/dy (V/cm^2)', 'nu_x (Hz)', 'nu_y (Hz)']
OPT_PRECISIONS = [2, 1, 2, 2, 2, 2]
OPT_MAX = [13333., 180., 10000., 10000., 300., 300.]
OPT_MIN = [-13333., -180., -10000., -10000., -300., -300.]

SYM_FIELDS = ['EastWest', 'UpperLowerEqual', 'UpperLowerNegative']
SYM_LONG = ['East = West?', 'Upper = Lower?', 'Upper = (-1)*Lower?']

SpacingMagicNumber = 110

class OptimizationDialog(QtGui.QDialog):
	def __init__(self, calculator, values, comp_shim):
		super(OptimizationDialog, self).__init__()
		self.comp_shim = comp_shim
		self.values = values
		self.calculator = calculator

		self.results = {}

		self.populate()

	def populate(self):
		self.layout = QtGui.QVBoxLayout()

		self.forms = OptimizationForms()
		self.forms.eInput.setValues(self.values)
		self.forms.pInput.setValues(self.calculator.parametersDump(self.compShimCorrection(self.values, self.comp_shim)))

		self.optimizeButton = QtGui.QPushButton('Optimize!')
		self.optimizeButton.clicked.connect(self.optimize)
		self.optimizeButton.setDefault(False)
		self.optimizeButton.setAutoDefault(False)

		self.okButton = QtGui.QPushButton('Set values')
		self.okButton.setDefault(False)
		self.okButton.setAutoDefault(False)
		self.okButton.setEnabled(False)

		self.cancelButton = QtGui.QPushButton('Cancel')
		self.cancelButton.setDefault(False)
		self.cancelButton.setAutoDefault(False)

		self.okButton.clicked.connect(self.accept)
		self.cancelButton.clicked.connect(self.reject)

		self.layout.addWidget(self.forms)
		self.layout.addWidget(self.optimizeButton)
		self.layout.addWidget(self.okButton)
		self.layout.addWidget(self.cancelButton)

		self.setLayout(self.layout)

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

	def buttonsEnable(self, enable):
		self.optimizeButton.setEnabled(enable)
		self.okButton.setEnabled(enable)
		self.optimizeButton.repaint()
		self.okButton.repaint()

	# Very clunky implementation, very slow...
	# Let's try to fix the speed later...
	def optimize(self):
		self.buttonsEnable(False)

		guesses = self.forms.eInput.getValues()
		ps = self.forms.pInput.getValues()
		checks = self.forms.pInput.getChecks()
		symmetries = self.forms.sInput.getChecks()

		table = self.calculator.getParameterFunctionTable()

		ks = []
		for k, v in checks.items():
			if v:
				ks.append(k)

		(vs_guesses, VsToEvs) = applySymmetries(guesses, symmetries)

		def opt(vs):
			ev = VsToEvs(vs)
			return np.array([ps[k] - table[k](ev) for k in ks])

		start = timeit.default_timer()
		res = least_squares(opt, vs_guesses)
		stop = timeit.default_timer()

		print("Fitting complete. n iter: {}, time per iter: {}".format(res.nfev, (stop-start)/float(res.nfev)))

		vs_results = self.calculator.EArrayToDict(VsToEvs(res.x))
		params_results = self.calculator.parametersDump(vs_results)

		self.forms.pResults.setValues(params_results)
		self.forms.eResults.setValues(vs_results)

		self.results = self.compShimCorrection(vs_results, (-1.0)*float(self.comp_shim))
		
		self.buttonsEnable(True)

	def getResults(self):
		return self.results

def applySymmetries(guesses, symmetries):
	if symmetries['EastWest'] and symmetries['UpperLowerEqual']:
		vs_guesses = np.array([guesses['LP'], guesses['LW']])
		def VsToEvs(vs):
			# [LP, UP, LW, LE, UW, UE]
			return [vs[0], -vs[0], vs[1], vs[1], vs[1], vs[1]]

	elif symmetries['EastWest'] and symmetries['UpperLowerNegative']:
		vs_guesses = np.array([guesses['LP'], guesses['LW']])
		def VsToEvs(vs):
			# [LP, UP, LW, LE, UW, UE]
			return [vs[0], -vs[0], vs[1], vs[1], -vs[1], -vs[1]]

	elif symmetries['EastWest']:
		vs_guesses = np.array([guesses['LP'], guesses['LW'], guesses['UW']])
		def VsToEvs(vs):
			# [LP, UP, LW, LE, UW, UE]
			return [vs[0], -vs[0], vs[1], vs[1], vs[2], vs[2]]

	elif symmetries['UpperLowerEqual']:
		vs_guesses = np.array([guesses['LP'], guesses['LW'], guesses['LE']])
		def VsToEvs(vs):
			# [LP, UP, LW, LE, UW, UE]
			return [vs[0], -vs[0], vs[1], vs[2], vs[1], vs[2]]

	elif symmetries['UpperLowerNegative']:
		vs_guesses = np.array([guesses['LP'], guesses['LW'], guesses['LE']])
		def VsToEvs(vs):
			# [LP, UP, LW, LE, UW, UE]
			return [vs[0], -vs[0], vs[1], vs[2], -vs[1], -vs[2]]

	else:
		vs_guesses = np.array([guesses['LP'], guesses['LW'], guesses['LE'], guesses['UW'], guesses['UE']])
		def VsToEvs(vs):
			# [LP, UP, LW, LE, UW, UE]
			return [vs[0], -vs[0], vs[1], vs[2], vs[3], vs[4]]
	return (vs_guesses, VsToEvs)


class OptimizationForms(QtGui.QWidget):
	def __init__(self):
		super(OptimizationForms, self).__init__()
		self.populate()

	def populate(self):
		self.layout = QtGui.QHBoxLayout()

		self.pInput = ParameterInputForm()
		self.sInput = SymmetriesForm()
		self.eInput = ElectrodeGuessForm()
		self.pResults = ParameterResultsForm()
		self.eResults = ElectrodeResultsForm()

		self.layout.addWidget(self.pInput)
		self.layout.addWidget(self.sInput)
		self.layout.addWidget(self.eInput)
		self.layout.addWidget(self.pResults)
		self.layout.addWidget(self.eResults)

		self.setLayout(self.layout)

class OptimizationInputForm(QtGui.QWidget):
	def __init__(self, config, checkbox):
		super(OptimizationInputForm, self).__init__()
		self.checkbox = checkbox
		self.config = config
		self.populate()

	def populate(self):
		self.layout = QtGui.QGridLayout()

		self.header = QtGui.QLabel(self.config['title'])
		self.layout.addWidget(self.header, 0, 0, 1, 2)

		self.lookup = {}
		self.widgets = []
		for i, (f, p, mi, ma) in enumerate(zip(self.config['fields'], self.config['precisions'], self.config['min'], self.config['max'])):
			self.lookup[f] = i

			value = QtGui.QDoubleSpinBox()
			value.setDecimals(p)
			value.setRange(mi, ma)	

			if 'long' in self.config:
				l = self.config['long'][i]
			else:
				l = f

			if self.checkbox:
				w = QtGui.QCheckBox(l)
				w.setChecked(True)
				w.stateChanged.connect(value.setEnabled)
			else:
				w = QtGui.QLabel(l)

			self.layout.addWidget(w, i+1, 0, 1, 1)
			self.layout.addWidget(value, i+1, 1, 1, 1)
			self.widgets.append((w, value))

		self.setLayout(self.layout)

	def getValues(self):
		values = {}

		for k,v in self.lookup.items():
			values[k] = self.widgets[v][-1].value()

		return values

	def setValues(self, values):
		for k, v in values.items():
			if k in self.lookup:
				self.widgets[self.lookup[k]][-1].setValue(float(v))


class OptimizationResultsForm(QtGui.QWidget):
	def __init__(self, config):
		super(OptimizationResultsForm, self).__init__()
		self.config = config
		self.populate()

	def populate(self):
		self.layout = QtGui.QGridLayout()

		self.header = QtGui.QLabel(self.config['title'])
		self.layout.addWidget(self.header, 0, 0, 1, 2)

		self.lookup = {}
		self.widgets = []
		for i, f in enumerate(self.config['fields']):
			self.lookup[f] = i

			label = QtGui.QLabel(f)
			edit = QtGui.QLineEdit()
			edit.setReadOnly(True)
			edit.setAlignment(QtCore.Qt.AlignRight)

			self.layout.addWidget(label, i+1, 0, 1, 1)
			self.layout.addWidget(edit, i+1, 1, 1, 1)
			self.widgets.append((label, edit))

		self.setLayout(self.layout)

	def setValues(self, values):
		for k, v in values.items():
			if k in self.lookup:
				index = self.lookup[k]
				precision = self.config['precisions'][index]
				self.widgets[index][-1].setText("{0:+0.{precision}f}".format(v, precision=precision))

class ParameterInputForm(OptimizationInputForm):
	config = {
		'title': 'Parameter input',
		'fields': OPT_FIELDS,
		'long': OPT_LONG,
		'precisions': OPT_PRECISIONS,
		'max': OPT_MAX,
		'min': OPT_MIN
	}

	def __init__(self):
		super(ParameterInputForm, self).__init__(self.config, True)
	
	def getChecks(self):
		checks = {}
		for k, v in self.lookup.items():
			checks[k] = self.widgets[v][0].isChecked()
		return checks

class ParameterResultsForm(OptimizationResultsForm):
	config = {
		'title': 'Parameter results',
		'fields': OPT_FIELDS,
		'precisions': OPT_PRECISIONS
	}
	def __init__(self):
		super(ParameterResultsForm, self).__init__(self.config)


class ElectrodeGuessForm(OptimizationInputForm):
	config = {
		'title': 'Initial guess',
		'fields': FORM_FIELDS['i'],
		'precisions': FIELD_PRECISIONS['i'],
		'max': FIELD_MAX['i'],
		'min': FIELD_MIN['i']
	}
	def __init__(self):
		super(ElectrodeGuessForm, self).__init__(self.config, False)

class ElectrodeResultsForm(OptimizationResultsForm):
	config = {
		'title': 'Fit results',
		'fields': FORM_FIELDS['i'],
		'precisions': FIELD_PRECISIONS['i']
	}
	def __init__(self):
		super(ElectrodeResultsForm, self).__init__(self.config)

class SymmetriesForm(QtGui.QWidget):
	config = {
		'fields': SYM_FIELDS,
		'long': SYM_LONG
	}
	def __init__(self):
		super(SymmetriesForm, self).__init__()
		self.populate()

	def populate(self):
		self.layout = QtGui.QVBoxLayout()

		self.header = QtGui.QLabel('Helpful symmetries')
		self.layout.addWidget(self.header)

		self.widgets = []
		self.lookup = {}
		for i, (f, l) in enumerate(zip(self.config['fields'], self.config['long'])):
			self.lookup[f] = i
			w = QtGui.QCheckBox(l)
			self.layout.addWidget(w)
			self.widgets.append(w)
		self.layout.addSpacing(SpacingMagicNumber)

		self.equal = self.widgets[self.lookup['UpperLowerEqual']]
		self.negative = self.widgets[self.lookup['UpperLowerNegative']]	
	
		self.equal.clicked.connect(self.equalClicked)
		self.negative.clicked.connect(self.negativeClicked)

		self.setLayout(self.layout)
	
	def getChecks(self):
		checks = {}
		for k,v in self.lookup.items():
			checks[k] = self.widgets[v].isChecked()
		return checks

	def equalClicked(self):
		if self.equal.isChecked():
			self.negative.setChecked(False)

	def negativeClicked(self):
		if self.negative.isChecked():
			self.equal.setChecked(False)
		

