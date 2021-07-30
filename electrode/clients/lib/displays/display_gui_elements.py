import json
import time
import numpy as np
import os
import sys

from PyQt4 import QtGui, QtCore, Qt
from PyQt4.QtCore import pyqtSignal 
from twisted.internet.defer import inlineCallbacks

from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt4agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

from matplotlib import pyplot as plt
from matplotlib import cm, colors, patches, collections

from pathlib import Path
sys.path.append([str(i) for i in Path(__file__).parents if str(i).endswith("labrad_tools")][0])
from electrode.calibrations import *

ROD_LIMIT = DAC_LIMIT * 2000.

COLORMAP = 'RdBu'

SEP = os.path.sep

GEOMETRY = {
	'ES' : {'width': 400},
}

ROD_COORDS = [
	# Lower West Rod
	{'center': (-3,-2.), 'rad': 0.5, 'name': 'LW'},
	# Lower East Rod
	{'center': (3,-2.), 'rad': 0.5, 'name': 'LE'},
	# Upper West Rod
	{'center': (-3,2.), 'rad': 0.5, 'name': 'UW'},
	# Upper East Rod
	{'center': (3,2.), 'rad': 0.5, 'name': 'UE'},
]

PLATE_COORDS = [
	# Lower Plate
	{'x0': (-6, -4), 'width': 12, 'height': 1, 'name': 'LP'},
	# Upper Plate
	{'x0': (-6, 3), 'width': 12, 'height': 1, 'name': 'UP'},
]

class ElectrodeSchematic(QtGui.QWidget):
	def __init__(self):
		super(ElectrodeSchematic, self).__init__()
		self.populate()
		self.setFixedWidth(GEOMETRY['ES']['width'])
		self.setupColorbar(-1, 1)

	def populate(self):
		self.layout = QtGui.QHBoxLayout()

		self.figure = Figure()
		self.canvas = FigureCanvas(self.figure)
		self.layout.addWidget(self.canvas)
		self.setLayout(self.layout)

	def setupColorbar(self, vmin, vmax):
		norm = colors.Normalize(vmin=vmin, vmax=vmax, clip=True)
		self.mapper = cm.ScalarMappable(norm=norm, cmap=COLORMAP)
		self.mapper.set_array(np.arange(vmin, vmax))
		self.colorbar =	self.figure.colorbar(self.mapper, orientation='vertical')
		self.colorbar.set_label('Volts')

	def redraw(self, values):
		self.figure.clear()
		self.ax = self.figure.gca()

		ps = []
		vals = []
		for x in PLATE_COORDS:
			ps.append(patches.Rectangle(x['x0'], x['width'], x['height'], ec='k'))
			vals.append(values[x['name']])
		for x in ROD_COORDS:
			ps.append(patches.Circle(x['center'], x['rad'], ec='k'))
			vals.append(values[x['name']])
		vals = np.array(vals)

		if np.min(vals) != np.max(vals):
			vmin = np.min(vals)
			vmax = np.max(vals)
		else:
			vmin = vals[0] - 1
			vmax = vals[0] + 1
		self.setupColorbar(vmin, vmax)

		self.ax.axis('equal')
		self.ax.axis('off')

		collection = collections.PatchCollection(ps, cmap=COLORMAP, clim=(vmin, vmax), alpha=1)
		collection.set_array(vals)

		self.ax.add_collection(collection)

		self.ax.set_xlim(-8, 8)
		self.ax.set_ylim(-5, 5)

		self.figure.tight_layout()
		self.canvas.draw()

class FieldSlicesWindow(QtGui.QWidget):
	def __init__(self, calculator):
		super(FieldSlicesWindow, self).__init__()
		self.calculator = calculator
		self.populate()

	def populate(self):
		self.layout = QtGui.QHBoxLayout()

		self.E = EWindow(self.calculator)
		self.E.setToolTip("Field cuts, assuming CompShim has zeroed linear gradient")
		self.U = UWindow(self.calculator)
		self.U.setToolTip("Potential cuts, assuming CompShim has zeroed linear gradient")

		self.layout.addWidget(self.E)
		self.layout.addWidget(self.U)

		self.setLayout(self.layout)

	def update(self, ev):
		self.E.updatePlot(ev)
		self.U.updatePlot(ev)

class AbstractWindow(QtGui.QWidget):
	def __init__(self, calculator):
		super(AbstractWindow, self).__init__()
		self.calculator = calculator
		self.populate()
		self.setupFigure()

	def populate(self):
		self.layout = QtGui.QHBoxLayout()

		self.figure = Figure()
		self.canvas = FigureCanvas(self.figure)
		self.layout.addWidget(self.canvas)

		self.setLayout(self.layout)

	def setupFigure(self):
		self.ax = self.figure.gca()

class EWindow(AbstractWindow):
	xr = [-1, 1] # mm
	yr = [-1, 1] # mm
	def __init__(self, calculator):
		super(EWindow, self).__init__(calculator)
	
	def updatePlot(self, ev):
		self.ax.clear()

		x = np.arange(self.xr[0], self.xr[1], 0.01)
		y = np.arange(self.yr[0], self.yr[1], 0.01)
		self.ax.plot(x, self.calculator.E(ev)(x,0), 'y-', label='x')
		self.ax.plot(y, self.calculator.E(ev)(0,y), 'g-', label='y')
		self.ax.legend()

		self.ax.set_xlabel('Position (mm)')
		self.ax.set_ylabel('|E| (V/cm)')

		self.figure.tight_layout()
		self.canvas.draw()

class UWindow(AbstractWindow):
	xr = [-100, 100] # um
	yr = [-100, 100] # um
	def __init__(self, calculator):
		super(UWindow, self).__init__(calculator)

	def updatePlot(self, ev):
		self.ax.clear()

		x = np.arange(self.xr[0], self.xr[1], 1.0)
		y = np.arange(self.yr[0], self.yr[1], 1.0)

		U0 = self.calculator.U(ev)(0,0)
		self.ax.plot(x, self.calculator.U(ev)(x/1000.0,0) - U0, 'y-', label='x')
		self.ax.plot(y, self.calculator.U(ev)(0,y/1000.0) - U0, 'g-', label='y')
		self.ax.legend()

		self.ax.set_xlabel(r'Position ($\mu$m)')
		self.ax.set_ylabel(r'$U - U_0$ ($\mu$K)')

		self.figure.tight_layout()
		self.canvas.draw()