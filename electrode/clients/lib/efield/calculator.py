from __future__ import absolute_import
import json
import time
import numpy as np
from numpy.polynomial.polynomial import polyval, polyval2d, polyder
from scipy.optimize import least_squares
import os
import sys

from copy import deepcopy

sys.path.append('./../')
from helpers import json_load_byteified

# This is a 4th order polynomial approximation
# of the KRb dipole moment as a function of E (in kV/cm)
from .dipole_fit import *

# 1 D = 3.33564e-30 Coulomb meters
# We usually use V/cm
DVcmToJ = 3.33564e-28
kB = 1.38e-23
amu = 1.66e-27

# Small epsilon for calculating derivatives at (x,y) = (epsilon, epsilon).
# This only matters when calculating quadrupole-like field configurations
# where the field is zero near the origin.
EPSILON = 1e-9

# Order of electrodes for lists
KEY_ORDER = ['LP', 'UP', 'LW', 'LE', 'UE', 'UW']

class ECalculator(object):
	""" Class for electric field calculations
	
	Calculates various derivatives of E
	and physically important quantities
	like the force and effective trapping frequency
	experienced by the molecules.

	Calculations are based on a COMSOL finite element simulation of
	our electrode geometry. We use a 7th order polynomial
	fit to the data (found in ./data/) to approximate the potential
	due to each electrode.

	Arguments
	---------
	path : str
		path to a JSON file containing the fitted electrode polynomials

	"""

	def __init__(self, path):
		self.path = path
		self.poly = np.array(D_POLY_FIT)
		self.key_order = KEY_ORDER
		self.getCoeffs()

		self.V = Potential(self.coeffs_array)

	#########################
	### Utility functions ###
	#########################
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

	def getParameterFunctionTable(self):
		r = {
			'Bias': self.bias,
			'Dipole': self.dipole_center,
			'Angle': self.angle,
			'dEdx': self.dEdx_center,
			'dEdy': self.dEdy_center,
			'Fx': self.Fx,
			'Fy': self.Fy,
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

	###################################
	### KRb dipole moment functions ###
	###################################
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

	############################################
	############################################
	# Electric field and its derivatives,
	# functions of np.array of electrode values
	############################################
	############################################
	def _Ex(self,ea):
		return self.V.d(1,0,ea)

	def _Ey(self,ea):
		return self.V.d(0,1,ea)

	def _E(self, ea):
		def fE(x,y):
			return np.sqrt(np.square(self._Ex(ea)(x,y)) + np.square(self._Ey(ea)(x,y)))
		return fE

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

	############################################
	############################################
	# Potential energy and its derivatives,
	# functions of np.array of electrode values
	############################################
	############################################
	def _U(self, ea):
		def fU(x,y):
			return -self.dipole(self._E(ea)(x,y)) * self._E(ea)(x,y) * DVcmToJ * 1e6 / kB
		return fU

	def _dUdx(self, ea):
		E = self._E(ea)(0,0)
		D = self.dipole(E)
		dEdx = self._dEdx(ea)(0,0)
		dDdE = self.dDdE(E)

		# Want J/m
		units = 10. * DVcmToJ
		return -1.0 * units * (E*dDdE*dEdx + D*dEdx)

	def _dUdy(self, ea):
		E = self._E(ea)(0,0)
		D = self.dipole(E)
		dEdy = self._dEdy(ea)(0,0)
		dDdE = self.dDdE(E)

		# Want J/m
		units = 10. * DVcmToJ
		return -1.0 * units * (E*dDdE*dEdy + D*dEdy)

	def _xQuadCoeffU(self, ea):
		E = self._E(ea)(0,0)
		D = self.dipole(E)

		d2Edx2 = self._xQuadraticCoeff(ea)
		d2Ddx2 = self.d2DdE2(E) * np.square(self._dEdx(ea)(0,0)) + self.dDdE(E) * d2Edx2
		
		# Want J / m^2
		units = 100. * DVcmToJ
		return -1.0 * units * (E*d2Ddx2 + D*d2Edx2 + 2.0*np.square(self._dEdx(ea)(0,0))*self.dDdE(E))

	def _yQuadCoeffU(self, ea):
		E = self._E(ea)(0,0)
		D = self.dipole(E)

		d2Edy2 = self._yQuadraticCoeff(ea)
		d2Ddy2 = self.d2DdE2(E) * np.square(self._dEdy(ea)(0,0)) + self.dDdE(E) * d2Edy2

		# Want J / m^2
		units = 100. * DVcmToJ
		return -1.0 * units * (E*d2Ddy2 + D*d2Edy2 + 2.0*np.square(self._dEdy(ea)(0,0))*self.dDdE(E))

	########################################################
	########################################################
	# Wrappers for electric field/potential energy functions
	# that accept a dict of electrode values for convenience
	#########################################################
	#########################################################
	def Ex(self,ev):
		return self._Ex(self.EDictToArray(ev))
	def Ey(self,ev):
		return self._Ey(self.EDictToArray(ev))
	def E(self, ev):
		return self._E(self.EDictToArray(ev))
	def dEdx(self, ev):
		return self._dEdx(self.EDictToArray(ev))
	def dEdy(self, ev):
		return self._dEdy(self.EDictToArray(ev))
	def xQuadraticCoeff(self, ev):
		return self._xQuadraticCoeff(self.EDictToArray(ev))
	def yQuadraticCoeff(self, ev):
		return self._yQuadraticCoeff(self.EDictToArray(ev))

	def U(self, ev):
		return self._U(self.EDictToArray(ev))
	def dUdx(self, ev):
		return self._dUdx(self.EDictToArray(ev))
	def dUdy(self, ev):
		return self._dUdy(self.EDictToArray(ev))
	def xQuadCoeffU(self, ev):
		return self._xQuadCoeffU(self.EDictToArray(ev))
	def yQuadCoeffU(self, ev):
		return self._yQuadCoeffU(self.EDictToArray(ev))

	###################################
	###################################
	# Physical quantities of interest
	# that are displayed in the GUI
	###################################
	###################################
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

	def Fx(self, ea):
		# nK/micron
		return float(-self._dUdx(ea) / kB * 1e9 * 1e-6)

	def Fy(self, ea):
		# nK/micron
		return float(-self._dUdy(ea) / kB * 1e9 * 1e-6)

	def nux(self, ea):
		cx = self._xQuadCoeffU(ea)
		return float(np.sign(cx) * np.sqrt(np.abs(cx) / (127.0*amu) / (2*np.pi)))

	def nuy(self, ea):
		cy = self._yQuadCoeffU(ea)
		return float(np.sign(cy) * np.sqrt(np.abs(cy) / (127.0*amu)/ (2*np.pi)))


class Potential(object):
	""" Returns derivatives of the potential

	Arguments
	---------
	coeffs : numpy array
		3-dimensional array of all polynomial coefficients; 0th dim: electrode index in the order of KEY_ORDER; 1st and 2nd dim: x and y polynomial coeffs

	Methods
	-------
	d(xord, yord, ev_array)
		Returns derivatives of the electric potential
	"""

	def __init__(self, coeffs):
		self.coeffs = coeffs


	def d(self, xord, yord, ev_array):
		""" Returns -1.0*(d**xord/dx**xord)(d**yord/dy**ord)V(x,y)
		
		Units: V/cm**(xord + yord)

		Note that self.coeffs has the following form:
			axis 0: electrode index (LP, UP, LW, LE, UW, UE)
			axis 1: x polynomial coeffs
			axis 2: y polynomial coeffs

		Parameters
		----------
		xord : int
			Number of x derivatives
		yord : int
			Number of y derivatives
		ev_array : numpy array
			Array of electrode potentials, same order as KEY_ORDER

		Returns
		-------
		function
			A function dV(x,y) = -1.0*(d**xord/dx**xord)(d**yord/dy**ord)V(x,y)
		"""
		valarr = polyder(self.coeffs, xord, axis=1)
		valarr = polyder(valarr, yord, axis=2)
		valarr = np.transpose(np.array(valarr), (1,2,0))

		def dV(x,y):
			# -1.0 for convenience, because we eventually care about the electric field
			# Factors of 10 are to get to V/cm (poly interp data is in mm)
			return -1.0*(10.)**(xord+yord)*np.dot(ev_array, polyval2d(np.array(x).ravel(),np.array(y).ravel(),valarr))
		return dV
