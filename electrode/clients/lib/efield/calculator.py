import json
import time
import numpy as np
from numpy.polynomial.polynomial import Polynomial, polyval2d

from scipy.optimize import least_squares

import os
import sys

from copy import deepcopy

from matplotlib import pyplot as plt

from PyQt4 import QtGui, QtCore, Qt
from PyQt4.QtCore import pyqtSignal 
from twisted.internet.defer import inlineCallbacks

sys.path.append('./../')
from helpers import json_load_byteified

from dipole_fit import *

from numpy.polynomial.polynomial import polyval, polyval2d, polyder

MAX_PARTIALS = 4

DVcmToJ = 3.33564e-28
kB = 1.38e-23
amu = 1.66e-27

EPSILON = 1e-9

KEY_ORDER = ['LP', 'UP', 'LW', 'LE', 'UE', 'UW']

class ECalculator(object):
	def __init__(self, path):
		self.path = path
		self.poly = np.array(D_POLY_FIT)
		self.key_order = KEY_ORDER
		self.getCoeffs()

		self.V = Potential(self.coeffs_array)

	def dipole(self, E):
		# The fit coefficients were calculated for E in kV/cm
		return polyval(E/1000., self.poly)

	# This is d Dipole / d E 
	def dDdE(self, E):
		c = polyder(self.poly, 1)
		# Divide by 1000 because E was in kV/cm for fit
		return polyval(E.ravel()/1000., c) / 1000.

	# This is d^2 dipole / d E^2
	def d2DdE2(self, E):
		c = polyder(self.poly, 2)
		# Divide by 1000 because E was in kV/cm for fit
		return polyval(E.ravel()/1000., c) / 1000. / 1000.

	def getCoeffs(self):
		self.coeffs_array = []
		with open(self.path, 'r') as f:
			self.coeffs = json_load_byteified(f)
		for key in self.key_order:
			val = np.array(self.coeffs[key])
			dx = np.shape(val)
			dx = int(np.sqrt(dx))

			val = val.reshape((dx, dx))
			self.coeffs[key] = val
			self.coeffs_array.append(val)
		self.coeffs_array = np.array(self.coeffs_array)

	def EDictToArray(self,ev):
		return np.array([ev[k] for k in self.key_order])

	def EArrayToDict(self,ea):
		return {k:v for k,v in zip(self.key_order, ea)}

	def _Ex(self,ea):
		return self.V.d(1,0,ea)

	def Ex(self,ev):
		return self._Ex(self.EDictToArray(ev))

	def _Ey(self,ea):
		return self.V.d(0,1,ea)

	def Ey(self,ev):
		return self._Ey(self.EDictToArray(ev))

	def _E(self, ea):
		def fE(x,y):
			return np.sqrt(np.square(self._Ex(ea)(x,y)) + np.square(self._Ey(ea)(x,y)))
		return fE

	def E(self, ev):
		return self._E(self.EDictToArray(ev))

	def _U(self, ea):
		def fU(x,y):
			return -self.dipole(self._E(ea)(x,y)) * self._E(ea)(x,y) * DVcmToJ * 1e6 / kB
		return fU
	
	def U(self, ev):
		return self._U(self.EDictToArray(ev))

	def _dEdx(self, ea):
		def fdEdx(x,y):
			Ex = self._Ex(ea)
			dExdx = self.V.d(2,0,ea)
			Ey = self._Ey(ea)
			dEydx = self.V.d(1,1,ea)

			if self._E(ea)(x,y).any() == 0:
				return 0
			else:
				return (Ex(x,y)*dExdx(x,y) + Ey(x,y)*dEydx(x,y))/self._E(ea)(x,y)
		return fdEdx

	def dEdx(self, ev):
		return self._dEdx(self.EDictToArray(ev))

	def _dEdy(self, ea):
		def fdEdy(x,y):
			Ex = self._Ex(ea)
			dExdy = self.V.d(1,1,ea)
			Ey = self._Ey(ea)
			dEydy = self.V.d(0,2,ea)

			if self._E(ea)(x,y).any() == 0:
				return 0
			else:
				return (Ex(x,y)*dExdy(x,y) + Ey(x,y)*dEydy(x,y))/self._E(ea)(x,y)
		return fdEdy

	def dEdy(self, ev):
		return self._dEdy(self.EDictToArray(ev))

	def _dUdx(self, ea):
		E = self._E(ea)(0,0)
		D = self.dipole(E)
		dEdx = self._dEdx(ea)(0,0)
		dDdE = self.dDdE(E)

		units = 10. * DVcmToJ
		return -1.0 * units * (E*dDdE*dEdx + D*dEdx)
	
	def dUdx(self, ev):
		return self._dUdx(self.EDictToArray(ev))

	def _dUdy(self, ea):
		E = self._E(ea)(0,0)
		D = self.dipole(E)
		dEdy = self._dEdy(ea)(0,0)
		dDdE = self.dDdE(E)

		units = 10. * DVcmToJ
		return -1.0 * units * (E*dDdE*dEdy + D*dEdy)

	def dUdy(self, ev):
		return self._dUdy(self.EDictToArray(ev))

	# Taylor expand around (0,0)
	def _xQuadraticCoeff(self, ea):
		d2Exdx2 = self.V.d(3,0,ea)(0,0)
		d2Eydx2 = self.V.d(2,1,ea)(0,0)
		dExdx = self.V.d(2,0,ea)(0,0)
		dEydx = self.V.d(1,1,ea)(0,0)
		Ex = self._Ex(ea)(0,0)
		Ey = self._Ey(ea)(0,0)

		first = -np.square(self._dEdx(ea)(0,0))
		second = (np.square(dExdx) + Ex*d2Exdx2 + np.square(dEydx) + Ey*d2Eydx2)

		if self._E(ea)(0,0).any() == 0:
			return 0
		else:
			return (first + second) / self._E(ea)(0,0)

	def xQuadraticCoeff(self, ev):
		return self._xQuadraticCoeff(self.EDictToArray(ev))

	# Taylor expand around (0,0)
	def _yQuadraticCoeff(self, ea):
		d2Exdy2 = self.V.d(1,2,ea)(0,0)
		d2Eydy2 = self.V.d(0,3,ea)(0,0)
		dExdy = self.V.d(1,1,ea)(0,0)
		dEydy = self.V.d(0,2,ea)(0,0)
		Ex = self._Ex(ea)(0,0)
		Ey = self._Ey(ea)(0,0)

		first = -np.square(self._dEdy(ea)(0,0))
		second = (np.square(dExdy) + Ex*d2Exdy2 + np.square(dEydy) + Ey*d2Eydy2)

		if self._E(ea)(0,0).any() == 0:
			return 0
		else:
			return (first + second) / self._E(ea)(0,0)

	def yQuadraticCoeff(self, ev):
		return self._yQuadraticCoeff(self.EDictToArray(ev))

	def _xQuadCoeffU(self, ea):
		E = self._E(ea)(0,0)
		D = self.dipole(E)

		d2Edx2 = self._xQuadraticCoeff(ea)
		d2Ddx2 = self.d2DdE2(E) * np.square(self._dEdx(ea)(0,0)) + self.dDdE(E) * d2Edx2

		units = 100. * DVcmToJ
		# J / m^2
		return -1.0 * units * (E*d2Ddx2 + D*d2Edx2 + 2.0*np.square(self._dEdx(ea)(0,0))*self.dDdE(E))

	def xQuadCoeffU(self, ev):
		return self._xQuadCoeffU(self.EDictToArray(ev))

	def _yQuadCoeffU(self, ea):
		E = self._E(ea)(0,0)
		D = self.dipole(E)

		d2Edy2 = self._yQuadraticCoeff(ea)
		d2Ddy2 = self.d2DdE2(E) * np.square(self._dEdy(ea)(0,0)) + self.dDdE(E) * d2Edy2

		units = 100. * DVcmToJ

		# J / m^2
		return -1.0 * units * (E*d2Ddy2 + D*d2Edy2 + 2.0*np.square(self._dEdy(ea)(0,0))*self.dDdE(E))

	def yQuadCoeffU(self, ev):
		return self._yQuadCoeffU(self.EDictToArray(ev))

	def bias(self, ea):
		return float(self._E(ea)(0,0))

	def dipole_center(self,ea):
		return float(self.dipole(self._E(ea)(0,0)))

	def angle(self, ea):
		return float(np.arctan2(self._Ex(ea)(0,0), self._Ey(ea)(0,0)) * 180. / np.pi)

	def dEdx_center(self, ea):
		return float(self._dEdx(ea)(EPSILON, EPSILON))

	def dEdy_center(self, ea):
		return float(self._dEdy(ea)(EPSILON, EPSILON))

	def nux(self, ea):
		cx = self._xQuadCoeffU(ea)
		return float(np.sign(cx) * np.sqrt(np.abs(cx) / (127.0*amu) / (2*np.pi)))

	def nuy(self, ea):
		cy = self._yQuadCoeffU(ea)
		return float(np.sign(cy) * np.sqrt(np.abs(cy) / (127.0*amu)/ (2*np.pi)))

	def getParameterFunctionTable(self):
		r = {
			'Bias': self.bias,
			'Dipole': self.dipole_center,
			'Angle': self.angle,
			'dEdx': self.dEdx_center,
			'dEdy': self.dEdy_center,
			'Fx': lambda ea: float(-self._dUdx(ea) / kB * 1e9 * 1e-6),
			'Fy': lambda ea: float(-self._dUdy(ea) / kB * 1e9 * 1e-6),
			'nux': self.nux, 
			'nuy': self.nuy 
		}
		return r

	def _parametersDump(self, ea):
		params = {}
		for k, v in self.getParameterFunctionTable().items():
			params[k] = v(ea)
		return params

	def parametersDump(self, ev):
		ea = self.EDictToArray(ev)
		return self._parametersDump(ea)

class Potential(object):
	def __init__(self, coeffs):
		self.coeffs = coeffs

	# Returns: -1.0 * (d^xord/dx^xord) (d^yord/dy^yord) V
	def d(self, xord, yord, ev_array):
		# self.coeffs:
		#	axis 0: electrode index (LP, UP, LW, LE, UW, UE)
		#	axis 1: x coeffs
		#	axis 2: y coeffs
		valarr = polyder(self.coeffs, xord, axis=1)
		valarr = polyder(valarr, yord, axis=2)
		valarr = np.transpose(np.array(valarr), (1,2,0))

		def dV(x,y):
			return -1.0*(10.)**(xord+yord)*np.dot(ev_array, polyval2d(np.array(x).ravel(),np.array(y).ravel(),valarr))
		return dV
