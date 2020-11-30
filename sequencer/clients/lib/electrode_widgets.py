from __future__ import absolute_import
import json
import numpy as np
import sys

import matplotlib
from PyQt4 import QtGui, QtCore, Qt
from PyQt4.QtCore import pyqtSignal 
matplotlib.use('Qt4Agg')
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt4agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

from .helpers import substitute_sequence_parameters
sys.path.append('../')
from devices.lib.ad5791_ramps import RampMaker

AD5791_PLOT_SCALE = 5 # Scale the thumbnail plots to +/- this value

class NameBox(QtGui.QLabel):
    clicked = QtCore.pyqtSignal()
    def __init__(self, nameloc):
        super(NameBox, self).__init__(None)
        self.nameloc = nameloc
        name, loc = nameloc.split('@')
        self.setText(name)
        self.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter  )
        self.name = name

    def mousePressEvent(self, x):
        self.clicked.emit()


class ElectrodeNameColumn(QtGui.QWidget):
    def __init__(self, channels):
        super(ElectrodeNameColumn, self).__init__(None)
        self.channels = channels
        self.populate()

    def populate(self):
        self.labels = {nl: NameBox(nl) for nl in self.channels}
        self.layout = QtGui.QVBoxLayout()
        self.layout.setSpacing(0)
        self.layout.setContentsMargins(10, 0, 0, 0)

        for i, nl in enumerate(sorted(self.channels, key=lambda nl: nl.split('@')[1])):
            self.layout.addWidget(self.labels[nl])
        self.layout.addWidget(QtGui.QWidget())
        self.setLayout(self.layout)


class ElectrodeArray(FigureCanvas):
    mouseover = pyqtSignal(int)

    def __init__(self, channels, config):
        self.channels = channels
        self.config = config
        self.rampMaker = RampMaker
        self.mouseover_col = -1
        self.populate()
       
    def populate(self):
        self.fig = Figure()
        FigureCanvas.__init__(self, self.fig)

        self.axes = self.fig.add_subplot(111)
        self.axes.spines['top'].set_visible(False)
        self.axes.spines['bottom'].set_visible(False)
        self.axes.spines['left'].set_visible(False)
        self.axes.spines['right'].set_visible(False)
        self.axes.get_xaxis().set_visible(False)
        self.axes.get_yaxis().set_visible(False)
        self.setContentsMargins(0, 0, 0, 0)
        self.fig.subplots_adjust(left=0, bottom = 0, right=1, top=1)

        self.on_move_id = self.mpl_connect('motion_notify_event', self.on_move)

    def plotSequence(self, sequence):
        self.axes.cla()
        for i, nl in enumerate(sorted(self.channels, key=lambda nl: nl.split('@')[1])):
            channel_sequence = sequence[nl]
            T, V = self.rampMaker(channel_sequence).get_plottable(scale='step')
            V = np.array(V) - i*2*AD5791_PLOT_SCALE
            self.axes.plot(T, V)
        for i in range(len(self.channels)-1):
            self.axes.axhline(-AD5791_PLOT_SCALE-i*2*AD5791_PLOT_SCALE, linestyle="--", color='grey')
        for i in range(len(sequence[self.config.timing_channel])-1):
            self.axes.axvline(i*99+98, color='grey')
        self.axes.set_ylim(-2*AD5791_PLOT_SCALE*len(self.channels)+AD5791_PLOT_SCALE, AD5791_PLOT_SCALE)
        self.axes.set_xlim(0, len(T))
        self.draw()

    def on_move(self, event):
        col = int(event.xdata / 99)
        if self.mouseover_col != col:
            self.mouseover_col = col
            self.mouseover.emit(self.mouseover_col)


class ElectrodeControl(QtGui.QWidget):
    def __init__(self, channels, config):
        super(ElectrodeControl, self).__init__(None)
        self.channels = channels
        self.config = config
        self.sequence = {}
        self._tooltips = []
        self.populate()

    def populate(self):
        self.nameColumn = ElectrodeNameColumn(self.channels)
        self.nameColumn.scrollArea = QtGui.QScrollArea()
        self.nameColumn.scrollArea.setWidget(self.nameColumn)
        self.nameColumn.scrollArea.setWidgetResizable(True)
        self.nameColumn.scrollArea.setHorizontalScrollBarPolicy(1)
        self.nameColumn.scrollArea.setVerticalScrollBarPolicy(1)
        self.nameColumn.scrollArea.setFrameShape(0)
       	
        self.array = ElectrodeArray(self.channels, self.config)
        self.array.scrollArea = QtGui.QScrollArea()
        self.array.scrollArea.setWidget(self.array)
        self.array.scrollArea.setWidgetResizable(True)
        self.array.scrollArea.setHorizontalScrollBarPolicy(1)
        self.array.scrollArea.setVerticalScrollBarPolicy(1)
        self.array.scrollArea.setFrameShape(0)

        self.vscroll = QtGui.QScrollArea()
        self.vscroll.setWidget(QtGui.QWidget())
        self.vscroll.setHorizontalScrollBarPolicy(1)
        self.vscroll.setVerticalScrollBarPolicy(2)
        self.vscroll.setFrameShape(0)
        
        self.layout = QtGui.QHBoxLayout()
        self.layout.addWidget(self.nameColumn.scrollArea)
        self.layout.addWidget(self.array.scrollArea)
        self.layout.addWidget(self.vscroll)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        self.setLayout(self.layout)

        self.connectWidgets()

    def displaySequence(self, sequence):
        self.sequence = sequence

    def updateParameters(self, parameter_values):
        plottable_sequence = substitute_sequence_parameters(self.sequence,
                                                            parameter_values)
        self.array.plotSequence(plottable_sequence)
    
    def connectWidgets(self):
        self.vscrolls = [self.nameColumn.scrollArea.verticalScrollBar(), 
                         self.array.scrollArea.verticalScrollBar(), 
                         self.vscroll.verticalScrollBar()]
        for vs in self.vscrolls:
            vs.valueChanged.connect(self.adjust_for_vscroll(vs))

        self.array.mouseover.connect(self.tooltipUpdate)

    def _setTooltips(self, tooltips):
        self._tooltips = tooltips

    def tooltipUpdate(self, c):
        try:
            self.setToolTip(self._tooltips[c])
        except Exception as e:
            pass

    def adjust_for_vscroll(self, scrolled):
        def afv():
            val = scrolled.value()
            for vs in self.vscrolls:
                vs.setValue(val)
        return afv

