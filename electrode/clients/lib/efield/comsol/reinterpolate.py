from __future__ import print_function
###########################################################################
# This script should be run once with FIT_FLAG = TRUE
# to calculate the polynomial interpolation of the E field.
# To increase precision it can be rerun with a larger POLY_ORDER.
# For POLY_ORDER = 1 (terms up to x^7 y^7), it takes about 3 minutes
# on the office computer.
###########################################################################

import json
import time
import numpy as np
from numpy.polynomial.polynomial import Polynomial, polyval2d

from scipy.optimize import least_squares

import os
import sys

from matplotlib import pyplot as plt

from PyQt4 import QtGui, QtCore, Qt
from PyQt4.QtCore import pyqtSignal 
from twisted.internet.defer import inlineCallbacks

PLOT_FLAG = False

FIT_FLAG = True

POLY_ORDER = 7

rel_path = './data/'

files = ['lp.txt', 'up.txt', 'lrl.txt', 'lrr.txt', 'url.txt', 'urr.txt']
names = ['LP', 'UP', 'LW', 'LE', 'UW', 'UE']

outfile = 'fit_coeffs.json'

def poly2d(p,order,x,y,z):
	ps = np.array(p).reshape((order+1,order+1))
	return polyval2d(x,y,ps) - z

def poly_sub(p, xx, yy, x):
    return np.ravel(poly7(xx,yy,p)- x)

data = []
for file in files:
	with open(rel_path + file, 'r') as f:
		data.append(np.loadtxt(f))

if PLOT_FLAG:
	for d in data:
		(dx, dz) = np.shape(d)
		dd = d[:,-1].reshape((int(np.sqrt(dx)), int(np.sqrt(dx))))

		plt.figure()
		plt.imshow(dd)
	plt.show()

if FIT_FLAG:
	# Data comes in as [[x, y, val], ...]
	fitted_parameters = {}
	for d,n in zip(data, names):
		guess = [0]*((POLY_ORDER+1)**2)
		res = least_squares(poly2d, guess, args=(POLY_ORDER, d[:,0], d[:,1], d[:,2]))
		fitted_parameters[n]=list(res.x)
		print("Done fitting")

	with open(rel_path + outfile, 'w') as f:
		f.write(json.dumps(fitted_parameters))