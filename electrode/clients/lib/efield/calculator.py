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

from numpy.polynomial.polynomial import polyval2d

MAX_PARTIALS = 3

DVcmToJ = 3.33564e-28
kB = 1.38e-23
amu = 1.66e-27

EPSILON = 1e-9

class ECalculator(object):
	def __init__(self, path):
		self.path = path
		self.poly = np.flip(np.array(D_POLY_FIT))
		self.getCoeffs()

		self.V = Potential(self.coeffs)
		self.functionTable = self.generateFunctionTable(MAX_PARTIALS)

	def dipole(self, E):
		# The fit coefficients were calculated for E in kV/cm
		return np.polyval(self.poly, E/1000.)

	# This is d Dipole / d E 
	def dDdE(self, E):
		x = np.flip(deepcopy(self.poly))
		for i in range(len(x)):
			x[i] *= i
		x = np.flip(x[1:])

		# Divide by 1000 because E was in kV/cm for fit
		return np.polyval(x, E/1000.) / 1000.

	# This is d^2 dipole / d E^2
	def d2DdE2(self, E):
		x = np.flip(deepcopy(self.poly))
		for i in range(len(x)):
			x[i] *= i*(i-1)
		x = np.flip(x[2:])

		# Divide by 1000 because E was in kV/cm for fit
		return np.polyval(x, E/1000.) / 1000. / 1000.

	def getCoeffs(self):
		with open(self.path, 'r') as f:
			self.coeffs = json_load_byteified(f)
		for key, val in self.coeffs.items():
			val = np.array(val)
			dx = np.shape(val)
			dx = int(np.sqrt(dx))
			self.coeffs[key] = val.reshape((dx, dx))

	def generateFunctionTable(self, depth):
		table = [0]*(depth**2)
		for i in range(depth):
			for j in range(depth):
				table[i*depth + j] = lambda ev: -1.0*self.V.d(j,i,ev)
		return table

	def E(self, ev):
		Ex = lambda x,y: -1.0*self.V.d(1,0,ev)(x,y)
		Ey = lambda x,y: -1.0*self.V.d(0,1,ev)(x,y)
		return lambda x,y: np.sqrt(np.square(Ex(x,y)) + np.square(Ey(x,y)))

	def U(self, ev):
		return lambda x,y: -self.dipole(self.E(ev)(x,y)) * self.E(ev)(x,y) * DVcmToJ * 1e6 / kB

	def dEdx(self, ev):
		Ex = lambda x,y: -1.0*self.V.d(1,0,ev)(x,y)
		dExdx = lambda x,y: -1.0*self.V.d(2,0,ev)(x,y)
		Ey = lambda x,y: -1.0*self.V.d(0,1,ev)(x,y)
		dEydx = lambda x,y: -1.0*self.V.d(1,1,ev)(x,y)

		return lambda x,y: 0 if self.E(ev)(x,y).any() == 0 else (Ex(x,y)*dExdx(x,y) + Ey(x,y)*dEydx(x,y))/self.E(ev)(x,y)

	def dEdy(self, ev):
		Ex = lambda x,y: -1.0*self.V.d(1,0,ev)(x,y)
		dExdy = lambda x,y: -1.0*self.V.d(1,1,ev)(x,y)
		Ey = lambda x,y: -1.0*self.V.d(0,1,ev)(x,y)
		dEydy = lambda x,y: -1.0*self.V.d(0,2,ev)(x,y)

		return lambda x,y: 0 if self.E(ev)(x,y).any() == 0 else (Ex(x,y)*dExdy(x,y) + Ey(x,y)*dEydy(x,y))/self.E(ev)(x,y)

	def dUdx(self, ev):
		E = self.E(ev)(0,0)
		D = self.dipole(E)
		dEdx = self.dEdx(ev)(0,0)
		dDdE = self.dDdE(E)

		units = 10. * DVcmToJ
		return -1.0 * units * (E*dDdE*dEdx + D*dEdx)

	def dUdy(self, ev):
		E = self.E(ev)(0,0)
		D = self.dipole(E)
		dEdy = self.dEdy(ev)(0,0)
		dDdE = self.dDdE(E)

		units = 10. * DVcmToJ
		return -1.0 * units * (E*dDdE*dEdy + D*dEdy)
	
	# Taylor expand around (0,0)
	def xQuadraticCoeff(self, ev):
		d2Exdx2 = -1.0*self.V.d(3,0,ev)(0,0)
		d2Eydx2 = -1.0*self.V.d(2,1,ev)(0,0)
		dExdx = -1.0*self.V.d(2,0,ev)(0,0)
		dEydx = -1.0*self.V.d(1,1,ev)(0,0)
		Ex = -1.0*self.V.d(1,0,ev)(0,0)
		Ey = -1.0*self.V.d(0,1,ev)(0,0)

		first = -np.square(self.dEdx(ev)(0,0))
		second = (np.square(dExdx) + Ex*d2Exdx2 + np.square(dEydx) + Ey*d2Eydx2)

		if self.E(ev)(0,0).any() == 0:
			return 0
		else:
			return (first + second) / self.E(ev)(0,0)

	# Taylor expand around (0,0)
	def yQuadraticCoeff(self, ev):
		d2Exdy2 = -1.0*self.V.d(1,2,ev)(0,0)
		d2Eydy2 = -1.0*self.V.d(0,3,ev)(0,0)
		dExdy = -1.0*self.V.d(1,1,ev)(0,0)
		dEydy = -1.0*self.V.d(0,2,ev)(0,0)
		Ex = -1.0*self.V.d(1,0,ev)(0,0)
		Ey = -1.0*self.V.d(0,1,ev)(0,0)

		first = -np.square(self.dEdy(ev)(0,0))
		second = (np.square(dExdy) + Ex*d2Exdy2 + np.square(dEydy) + Ey*d2Eydy2)

		if self.E(ev)(0,0).any() == 0:
			return 0
		else:
			return (first + second) / self.E(ev)(0,0)

	def xQuadCoeffU(self, ev):
		E = self.E(ev)(0,0)
		D = self.dipole(E)

		d2Edx2 = self.xQuadraticCoeff(ev)
		d2Ddx2 = self.d2DdE2(E) * np.square(self.dEdx(ev)(0,0)) + self.dDdE(E) * d2Edx2

		units = 100. * DVcmToJ
		# J / m^2
		return -1.0 * units * (E*d2Ddx2 + D*d2Edx2 + 2.0*np.square(self.dEdx(ev)(0,0))*self.dDdE(E))

	def yQuadCoeffU(self, ev):
		E = self.E(ev)(0,0)
		D = self.dipole(E)

		d2Edy2 = self.yQuadraticCoeff(ev)
		d2Ddy2 = self.d2DdE2(E) * np.square(self.dEdy(ev)(0,0)) + self.dDdE(E) * d2Edy2

		units = 100. * DVcmToJ

		# J / m^2
		return -1.0 * units * (E*d2Ddy2 + D*d2Edy2 + 2.0*np.square(self.dEdy(ev)(0,0))*self.dDdE(E))

	def parametersDump(self, ev):
		params = {}

		dip = self.dipole(self.E(ev)(0,0)) # Debye

		params['Bias'] = float(self.E(ev)(0,0))
		params['Dipole'] = float(dip)

		Ex = -1.0*self.V.d(1,0,ev)(0,0)
		Ey = -1.0*self.V.d(0,1,ev)(0,0)
		params['Angle'] = float(np.arctan2(Ex, Ey) * 180. / np.pi)

		params['dEdx'] = float(self.dEdx(ev)(EPSILON,EPSILON))
		params['dEdy'] = float(self.dEdy(ev)(EPSILON,EPSILON))
		
		params['Fx'] = float(-self.dUdx(ev) / kB * 1e9 * 1e-6)
		params['Fy'] = float(-self.dUdy(ev) / kB * 1e9 * 1e-6)
		
		cx = self.xQuadCoeffU(ev)
		signx = np.sign(cx)
		cx = np.abs(cx)

		cy = self.yQuadCoeffU(ev)
		signy = np.sign(cy)
		cy = np.abs(cy)

		params['nux'] = float(signx*np.sqrt(cx / (127.0 * amu) / (2*np.pi) ))
		params['nuy'] = float(signy*np.sqrt(cy / (127.0 * amu) / (2*np.pi) ))

		return params


class Potential(object):
	def __init__(self, coeffs):
		self.coeffs = coeffs

	def d(self, xord, yord, ev):
		valarr = []
		evarr = []
		for key,val in self.coeffs.items():
			evarr.append(ev[key])
			v = val
			
			for i in range(xord):
				v = self.ddx(v)
			for j in range(yord):
				v = self.ddy(v)
			valarr.append(v)

		valarr = np.transpose(np.array(valarr), (1,2,0))
		evarr = np.array(evarr)
		return lambda x, y: (10.)**(xord+yord)*np.dot(evarr, polyval2d(np.array(x).ravel(),np.array(y).ravel(),valarr))

	def ddx(self, coeffs):
		x = deepcopy(coeffs)
		(dy, dx) = np.shape(x)

		for i in range(dy):
			x[i,:] *= i

		return x[1:,:]

	def ddy(self, coeffs):
		y = deepcopy(coeffs)
		return self.ddx(y.T).T