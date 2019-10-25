import json
import time
import numpy as np
import os
import sys

from PyQt4 import QtGui, QtCore, Qt
from PyQt4.QtCore import pyqtSignal 
from twisted.internet.defer import inlineCallbacks

sys.path.append('../../')
from calibrations import *

# Form fields (short names)
FORM_FIELDS = {
	'i' : ['LP', 'UP', 'LW', 'LE', 'UW', 'UE'],
	'n' : ['GlobalOffset', 'Bias', 'RodScale', 'CompShim', 'HGrad', 'EastWest', 'RodOffset'],
	'p' : ['Bias', 'Dipole', 'Angle', 'dEdx', 'dEdy', 'Fx', 'Fy', 'nux', 'nuy'],
}

# Tooltips
TOOLTIPS = {
	'i' : {i : 'slope = {}, offset = {}'.format(EFC[i]['m'], EFC[i]['b']) for i in FORM_FIELDS['i']},
	'n' : {
		'GlobalOffset': 'V, global shift from 0',
		'Bias' : 'V/cm, nominal for flat field, includes 0.955 empirical factor',
		'RodScale' : 'rod_scale',
		'CompShim': 'V*Bias/{}, dE/dx, old comp_shim'.format(int(NORMALIZATION_FIELD)), 
		'HGrad' : 'V, dE/dx, old evap_grad',
		'EastWest' : 'V, positive E_x points from West to East',
		'RodOffset': 'V, additional shift from center of plates'
	}, 
	# 'cs' : {'cs' : 'V*Bias/{}, dE/dx, old comp_shim'.format(int(NORMALIZATION_FIELD))}
}

# Field precisions
FIELD_PRECISIONS = {
	'i' : [2, 2, 2, 2, 2, 2],
	'n' : [2, 2, 4, 2, 2, 2, 2, 2],
	'c' : [5, 5, 5, 5, 5, 5],
	'p' : [2, 3, 1, 2, 2, 2, 2, 2, 2],
	# 'cs': [2]
}

# Field mins for numeric entry
FIELD_MIN = {
	'i' : [-DAC_LIMIT*2000.]*6,
	'n' : [-3000., -13333., -5., -100., -1000., -1000., -3000.],
	# 'cs': [-100.]
}

# Field mins for numeric entry
FIELD_MAX = {
	'i' : [DAC_LIMIT*2000.]*6,
	'n' : [3000., 13333., 5., 100., 1000., 1000., 3000.],
	# 'cs' : [100.]
}

# Field steps
FIELD_STEP = {
	'i' : [0.01]*6,
	'n' : [1., 100., 0.0001, 0.1, 0.1, 0.1, 1.],
	# 'cs' : [0.1]
}


# Long names for monitor fields
MONITOR_FIELDS = {
	'c' : ['LP (SDAC0)', 'UP (SDAC1)', 'LW (SDAC2)', 'LE (SDAC3)', 'UW (SDAC4)', 'UE (SDAC5)'],
	'p' : ['Bias (V/cm)', 'Dipole (D)', 'Angle from vertical (deg)', 'd|E|/dx (V/cm^2)', 'd|E|/dy (V/cm^2)', 'Fx (nK/um)', 'Fy (nK/um)', 'nu_x (Hz)', 'nu_y (Hz)']
}

def DACsToVs(DACs):
	Vs = {}
	for key, val in DACs.items():
		Vs[key] = float(val)*EFC[key]['m'] + EFC[key]['b']
	return Vs

def VsToDACs(Vs):
	DACs = {}
	for key, val in Vs.items():
		DACs[key] = float(val - EFC[key]['b']) / EFC[key]['m']
	return DACs

def NormalModesToVs(NormalModes):
	Vs = {}
	PlateSpan = PLATE_SEPARATION * float(NormalModes['Bias']) / RODS_CORRECTION

	LPNoOffset = PlateSpan/2.0
	
	dEdx = NormalModes['HGrad'] + NormalModes['CompShim'] * NormalModes['Bias'] / NORMALIZATION_FIELD
	ew = NormalModes['EastWest']
	
	Vs['LP'] = LPNoOffset + NormalModes['GlobalOffset']
	Vs['UP'] = -LPNoOffset + NormalModes['GlobalOffset']

	x = LPNoOffset

	Vs['LW'] = NormalModes['GlobalOffset'] + NormalModes['RodOffset'] + NormalModes['RodScale']*x - dEdx + ew
	Vs['LE'] = NormalModes['GlobalOffset'] + NormalModes['RodOffset'] + NormalModes['RodScale']*x + dEdx - ew
	Vs['UW'] = NormalModes['GlobalOffset'] + NormalModes['RodOffset'] - NormalModes['RodScale']*x + dEdx + ew
	Vs['UE'] = NormalModes['GlobalOffset'] + NormalModes['RodOffset'] - NormalModes['RodScale']*x - dEdx - ew

	return Vs

def VsToNormalModes(Vs, comp_shim):
	NormalModes = {}

	# Global offset is average of LP and UP
	GlobalOffset = float(Vs['LP'] + Vs['UP']) / 2.0
	# Rod offset is the common mode thing (average), less the Global offset
	RodOffset = (Vs['LW'] + Vs['LE'] + Vs['UW'] + Vs['UE']) / 4.0 - GlobalOffset
	# Plate span for calculating field
	PlateSpan = Vs['LP'] - Vs['UP']

	LP = Vs['LP'] - GlobalOffset

	LW = Vs['LW'] - GlobalOffset - RodOffset
	UW = Vs['UW'] - GlobalOffset - RodOffset
	LE = Vs['LE'] - GlobalOffset - RodOffset
	UE = Vs['UE'] - GlobalOffset - RodOffset

	# We've removed the offsets. At this point, here is the system of equations we want to invert
	# LW = RS*LP - dEdx + ew
	# LE = RS*LP + dEdx - ew
	# UW = -RS*LP + dEdx + ew
	# UE = -RS*LP - dEdx - ew
	# where RS is rod scale, LP is the lower plate voltage (with offsets subtracted away),
	# dEdx is combined shim and evap grads, and ew is the East-West imbalance
	# Note that the quantities that should be scaled by the field are not yet

	ew = (LW + UW) / 2.0
	dEdx = (LE + UW) / 2.0

	if LP != 0:
		RS = (LW + LE) / 2.0 / LP
	else:
		RS = (LW + LE) / 2.0 # if Bias is 0, then just let Rod scale be the actual voltage, not normalized

	NormalModes['GlobalOffset'] = GlobalOffset
	NormalModes['Bias'] = float(PlateSpan) / PLATE_SEPARATION * RODS_CORRECTION
	NormalModes['RodScale'] = RS

	# Subtract scaled comp_shim
	dEdx -= comp_shim * (NormalModes['Bias'] / NORMALIZATION_FIELD)
	NormalModes['CompShim'] = comp_shim
	NormalModes['HGrad'] = dEdx

	NormalModes['EastWest'] = ew		
	NormalModes['RodOffset'] = RodOffset
	
	return NormalModes






