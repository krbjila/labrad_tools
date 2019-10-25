import json
import time
import numpy as np
import os
import sys

from copy import deepcopy

from PyQt4 import QtGui, QtCore, Qt
from PyQt4.QtCore import pyqtSignal 
from twisted.internet.defer import inlineCallbacks

from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt4agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from matplotlib.transforms import Bbox

sys.path.append('../sequencer/devices/lib/')
from analog_ramps import RampMaker as analogRampMaker
from ad5791_ramps import RampMaker as stableRampMaker

precisions = {
	'dt': 3,
	'span': 2
}

SEP = os.path.sep

class RegionSelector(QtGui.QWidget):
	region_changed = pyqtSignal(float, float)

	def __init__(self):
		super(RegionSelector, self).__init__()

		self.populate()

	def populate(self):
		self.layout = QtGui.QGridLayout()

		self.jumpLabel = QtGui.QLabel("Jump to module:")
		self.jumpControl = QtGui.QComboBox()
		self.jumpControl.activated.connect(self.emit_sig)

		self.dtLabel = QtGui.QLabel("Time offset from module (ms):")
		self.dtControl = QtGui.QDoubleSpinBox()
		self.dtControl.setDecimals(precisions['dt'])
		self.dtControl.setRange(-2000, 2000)
		self.dtControl.valueChanged.connect(self.emit_sig)

		self.spanLabel = QtGui.QLabel("Horizontal span (ms): ")
		self.spanControl = QtGui.QDoubleSpinBox()
		self.spanControl.setDecimals(precisions['span'])
		self.spanControl.setRange(-50000, 50000)
		self.spanControl.valueChanged.connect(self.emit_sig)

		row = 0
		self.layout.addWidget(self.jumpLabel, row, 0, 1, 1)
		self.layout.addWidget(self.jumpControl, row, 1, 1, 1)
		row += 1

		self.layout.addWidget(self.dtLabel, row, 0, 1, 1)
		self.layout.addWidget(self.dtControl, row, 1, 1, 1)
		row += 1

		self.layout.addWidget(self.spanLabel, row, 0, 1, 1)
		self.layout.addWidget(self.spanControl, row, 1, 1, 1)
		row += 1

		self.setLayout(self.layout)

	def emit_sig(self):
		ind = self.jumpControl.currentIndex()
		start = self.times[ind] + 1e-3*self.dtControl.value()	
		stop = min(start + 1e-3*self.spanControl.value(), self.max_time)

		if start == stop:
			if start == self.max_time:
				start -= 1e-3
			else:
				stop += 1e-3

		if start < 0:
			start = 0
			self.dtControl.setValue(1e3*(start - self.times[ind]))
		self.region_changed.emit(start, stop)


	def setModules(self, sequence_list):
		self.jumpControl.clear()

		for x in sequence_list:
			self.jumpControl.addItem(str(x))

	def setTimes(self, times):
		x = []
		for i in range(len(times)):
			if i == 0:
				x.append(0)
			else:
				x.append(x[i-1] + times[i-1])
		self.times = x

		self.max_time = self.times[-1] + times[-1]

		for i in range(self.jumpControl.count()):
			m = self.jumpControl.itemText(i)
			self.jumpControl.setItemText(i, m + " ({0:0.3f} s)".format(self.times[i]))

		self.dtControl.setValue(0)
		self.spanControl.setValue(1e3*times[self.jumpControl.currentIndex()])


class ImageWindow(QtGui.QWidget):
	# pixels to scroll per mousewheel event
	d = {"down" : 30, "up" : -30}
	region = (0, 1e-3)

	def __init__(self, digital_channels, analog_channels, timing_channel):
		super(ImageWindow, self).__init__()

		self.digital_channels = {}
		for v in digital_channels.values():
			self.digital_channels.update(v)

		self.analog_channels = {}
		for v in analog_channels.values():
			self.analog_channels.update(v)

		self.timing_channel = timing_channel

		self.active_channels = []
		self.legends = [[], []]
		self.populate()

	def populate(self):
		self.layout = QtGui.QVBoxLayout()

		self.figure = Figure()
		self.canvas = FigureCanvas(self.figure)
		self.toolbar = NavigationToolbar(self.canvas, self)

		self.axes = []
		self.axes = self.figure.subplots(2,1,True)
		self.figure.subplots_adjust(left=0.05, right=0.8, bottom=0.20, top=0.95)

		self.layout.addWidget(self.toolbar)
		self.layout.addWidget(self.canvas)
		self.setLayout(self.layout)

	def setActiveChannels(self, channels):
		self.active_channels = channels
		self.update()

	def setSequence(self, sequence):
		self.sequence = sequence
		self.update()

	def update(self):
		cropped_sequence = self.crop(self.sequence)
		active = {k: cropped_sequence[k] for k in self.active_channels}
		self.plottable = self.getPlottable(active)

		self.scaleToView(self.plottable)

		self.axes[0].clear()
		self.axes[1].clear()

		for k, v in sorted(self.plottable['digital'].items(), key=lambda k: k[0].split('@')[-1]):
			self.axes[0].plot(v[:,0], v[:,1], '-', label=k.split('@')[-1])
		for k, v in sorted(self.plottable['analog'].items(), key=lambda k: k[0].split('@')[-1]):
			self.axes[1].plot(v[:,0], v[:,1], '-', label=k.split('@')[-1])

		self.legends[0] = self.axes[0].legend(loc="upper left", bbox_to_anchor=(1., 0, 0.1, 1), ncol=3, markerscale=0.1, fontsize='small')
		self.legends[1] = self.axes[1].legend(loc="upper left", bbox_to_anchor=(1., 0, 0.1, 1), ncol=3, markerscale=0.1, fontsize='small')
		
		for ax in self.axes:
			ax.set_xlim(*self.region)

		self.axes[0].set_ylabel('Digital')
		self.axes[1].set_ylim((-1.1, 1.1))
		self.axes[1].set_yticks([-1, 0, 1])
		self.axes[1].set_ylabel('Scaled Analog')
		self.axes[1].set_xlabel('Time (s)')


		self.canvas.draw()

	def crop(self, sequence):
		(start, stop) = self.region

		seq = sequence[self.timing_channel]

		t = 0
		start_ind = len(seq) - 1
		for i, step in enumerate(seq):
			if t >= start:
				start_ind = i - 1
				break
			t += step['dt']
		start_ind = max(start_ind, 0)

		t = 0
		stop_ind = len(seq)
		for i, step in enumerate(seq):
			if t >= stop:
				stop_ind = i
				break
			t += step['dt']

		cropped = deepcopy(sequence)
		for k, v in cropped.items():
			cropped[k] = v[start_ind:(stop_ind+i)]

		return cropped


	def scaleToView(self, plottable):
		# (start_r, stop_r) = self.region

		# for v in self.plottable['digital'].values():
		# 	for i, step in enumerate(v):
		# 		if step[0] >= start:
		# 			start_ind_temp = i - 1
		# 			break
		# 	start_ind = max(min(start_ind_temp, i - 1), 0)

		# 	for i, step in enumerate(v):
		# 		if step[0] >= stop:
		# 			stop_ind_temp = i
		# 			break
		# 	stop_ind = min(stop_ind_temp, i)
		# 	v = v[start_ind:(stop_ind+1)]

		for v in self.plottable['analog'].values():
			# for i, step in enumerate(v):
			# 	if step[0] >= start:
			# 		start_ind_temp = i - 1
			# 		break
			# start_ind = max(min(start_ind_temp, i - 1), 0)

			# for i, step in enumerate(v):
			# 	if step[0] >= stop:
			# 		stop_ind_temp = i
			# 		break
			# stop_ind = min(stop_ind_temp, i)

			# max_val = np.max(v[start_ind:(stop_ind+1), 1])
			# min_val = np.min(v[start_ind:(stop_ind+1), 1])

			# scale = max(np.abs(max_val), np.abs(min_val))

			# v = v[start_ind:(stop_ind+1)]
			# if scale != 0:
			# 	v[:,1] = v[:,1]/scale


			max_val = np.max(v[:, 1])
			min_val = np.min(v[:, 1])

			scale = max(np.abs(max_val), np.abs(min_val))
			if scale != 0:
				v[:, 1] /= float(scale)


	def setRegion(self, start, stop):
		self.region = (start, stop)
		self.update()

	def getPlottable(self, active):
		plottable = {'digital': {}, 'analog': {}}

		for k,v in active.items():
			seq = []
			t = 0

			# If digital channel, simply append tuples of (time, output)
			if self.digital_channels.has_key(k):
				# Append the last value also to get square edges on the waveform!
				last = 0
				for x in v:	
					seq.append([t, last])
					seq.append([t, x['out']])

					t += x['dt']
					last = x['out']
				seq.append([t, last])

				# Invert if needed
				if self.digital_channels[k]['invert']:
					seq = [(tt, (vv-1.0)*-1.0) for tt, vv in seq]

				plottable['digital'][k] = np.array(seq)
			# If analog channel, have to get fancy
			else:
				# If normal analog board
				if self.analog_channels[k]['channel_type'] == 'analog':
					# Get ramp maker, generate programmable
					r = analogRampMaker(v)
					s = r.get_programmable()

					# For analog channels, programmables are in terms of delta voltages
					# Need to get the absolute voltages for plotting
					vv = 0
					for x in s:
						seq.append([t, vv])
						t += x['dt']
						vv += x['dv']
					seq.append([t, vv])

				# If stable board
				else:
					# Get ramp maker, generate programmable
					r = stableRampMaker(v)
					s = r.get_programmable()

					# For stable channels, programmables are in absolute voltages
					last = 0
					seq.append([t, last])

					for x in s:
						# seq.append([t, last])
						t += x['dt']
						seq.append([t, x['v']])
						

					seq.append([t, s[-1]['v']])
				plottable['analog'][k] = np.array(seq)
		return plottable