import json
import time
import numpy as np
import os
import sys

from copy import deepcopy

from PyQt4 import QtGui, QtCore, Qt
from PyQt4.QtCore import pyqtSignal 
from twisted.internet.defer import inlineCallbacks

from pathlib import Path
sys.path.append([str(i) for i in Path(__file__).parents if str(i).endswith("labrad_tools")][0])
from electrode.clients.lib.displays.display_gui_elements import *

from electrode.calibrations import *

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

	def setValues(self, values, comp_shim):
		self.values = self.compShimCorrection(values, comp_shim)
		self.electrodeSchematic.redraw(self.values)
		self.fieldSlicesWindow.update(self.values)

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
