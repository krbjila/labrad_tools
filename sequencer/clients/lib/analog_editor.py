from __future__ import absolute_import
import sys
import json
from PyQt4 import QtGui, QtCore
from twisted.internet.defer import inlineCallbacks, returnValue
import numpy as np
import matplotlib
matplotlib.use('Qt4Agg')
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt4agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

sys.path.append('../../../client_tools')
from connection import connection
from widgets import SuperSpinBox
from .helpers import merge_dicts, get_sequence_parameters, substitute_sequence_parameters
sys.path.append('../')
from devices.lib.analog_ramps import RampMaker

from copy import deepcopy

class ParameterWidget(QtGui.QWidget):
    def __init__(self, ramp_type, ramp):
        """
        parameters is [(parameter_label, (range, suffixes, num_decimals)),]
        """
        super(ParameterWidget, self).__init__(None)
        self.ramp_type = ramp_type
        self.parameters = ramp.required_parameters

        # added 4/23/19
        self.default_values = ramp.default_values # dict with default values

        self.populate()

    def populate(self):
        self.layout = QtGui.QGridLayout()
        self.pboxes = {}
        if self.ramp_type is 'sub':
            r, s, n = dict(self.parameters)['dt']
            label, self.pboxes['dt'] = self.make_pbox('dt', r, s, n)
            self.subbox = QtGui.QTextEdit()
            self.subbox.setLineWrapMode(0)
            self.subbox.setFixedWidth(80+30+2)
            self.subbox.setFixedHeight(4*20)
            self.subbox.setHorizontalScrollBarPolicy(1)
            self.subbox.setVerticalScrollBarPolicy(1)
            self.subbox.setText('')
            self.edit_button = QtGui.QPushButton('Edit')
            self.layout.addWidget(self.subbox)
            self.layout.addWidget(self.edit_button)

        else:
            for i, (p,( r, s, n)) in enumerate(self.parameters):
                label, self.pboxes[p] = self.make_pbox(*(p, r, s, n))
                
                # added 4/23/19
                if p in self.default_values:
                    self.pboxes[p].display(self.default_values[p])

                self.layout.addWidget(QtGui.QLabel(label), i, 0)
                self.layout.addWidget(self.pboxes[p], i, 1)
        self.setFixedWidth(80+30+4)

        self.layout.setSpacing(0)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(QtGui.QFrame())
        self.setLayout(self.layout)

    def make_pbox(self, p, r, s, n):
        pbox = SuperSpinBox(r, s, n)
        pbox.display(1)
        label = QtGui.QLabel(p+': ')
        label.setFixedWidth(30)
        label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        pbox.setFixedWidth(80)
        pbox.setFixedHeight(20)
        return p, pbox

class RampColumn(QtGui.QGroupBox):
    def __init__(self, RampMaker):
        super(RampColumn, self).__init__(None)
        self.ramp_maker = RampMaker
        self.populate()

    def populate(self):
        self.add = QtGui.QPushButton('+')
        self.dlt = QtGui.QPushButton('-')
        self.ramp_select = QtGui.QComboBox()
        self.ramp_select.addItems(self.ramp_maker.available_ramps.keys())
        self.parameter_widgets = {k: ParameterWidget(k, ramp) for 
                k, ramp in self.ramp_maker.available_ramps.items()}
        self.stack = QtGui.QStackedWidget()
        for k, pw in self.parameter_widgets.items():
            self.stack.addWidget(pw)
        
        self.zero_button = QtGui.QPushButton('zero')
        self.prev_button = QtGui.QPushButton('previous')
        self.next_button = QtGui.QPushButton('next')        
#        self.all_zero = QtGui.QPushButton('all zero')

        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.add, 0, 0)
        self.layout.addWidget(self.dlt, 0, 1)
        self.layout.addWidget(self.ramp_select, 0, 2)
        self.layout.addWidget(self.stack, 1, 0, 1, 3)

        self.layout.addWidget(self.zero_button, 2, 2, 1, 2)
        self.layout.addWidget(self.prev_button, 3, 2, 1, 2)
        self.layout.addWidget(self.next_button, 4, 2, 1, 2)
#        self.layout.addWidget(self.all_zero, 5, 2, 1, 2)

        self.zero_button.setFixedSize(80, 20)
        self.prev_button.setFixedSize(80, 20)
        self.next_button.setFixedSize(80, 20)
#        self.all_zero.setFixedSize(80, 20)

        self.setLayout(self.layout)
        self.layout.setSpacing(0)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.add.setFixedSize(15, 20) # w, h
        self.dlt.setFixedSize(15, 20) # w, h
        self.ramp_select.setFixedWidth(80)
        self.ramp_select.setFixedHeight(20)
        self.setFixedWidth(30+80+4)

        self.ramp_select.currentIndexChanged.connect(self.select_from_stack)
        rs_def_index = self.ramp_select.findText('lin')
        self.ramp_type = 'lin'
        self.ramp_select.setCurrentIndex(rs_def_index)

    def select_from_stack(self):
        prev_ramp_type = self.ramp_type
        self.ramp_type = str(self.ramp_select.currentText())
        for p, i in self.parameter_widgets[prev_ramp_type].parameters:
            try:
                val = self.parameter_widgets[prev_ramp_type].pboxes[p].value()
                self.parameter_widgets[self.ramp_type].pboxes[p].display(val)
            except:
                pass
        self.stack.setCurrentWidget(self.parameter_widgets[self.ramp_type])

    def get_ramp(self):
        ramp_type = str(self.ramp_select.currentText())
        ramp = {'type': str(self.ramp_select.currentText())}
        if ramp['type'] != 'sub':
            ramp.update({k: b.value() for k, b in self.stack.currentWidget().pboxes.items()})
        else:
            ramp.update({'seq': eval('['+str(self.stack.currentWidget().subbox.toPlainText())+']')})
        return ramp

class RampTable(QtGui.QWidget):
    def __init__(self, RampMaker):
        QtGui.QDialog.__init__(self)
        self.ramp_maker = RampMaker
        self.populate()

    def populate(self):
        self.cols = [RampColumn(self.ramp_maker) for i in range(100)]
        self.layout = QtGui.QHBoxLayout()
        for c in self.cols:
            self.layout.addWidget(c)
        self.layout.addWidget(QtGui.QFrame())
        self.layout.setSpacing(2)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.setLayout(self.layout)

    def get_channel_sequence(self):
        return [c.get_ramp() for c in self.cols if not c.isHidden()]

class MplCanvas(FigureCanvas):
    def __init__(self):
        self.fig = Figure()
        self.axes = self.fig.add_subplot(111)
        self.axes.hold(False)


        self.fig.set_tight_layout(True)

        FigureCanvas.__init__(self, self.fig)
        self.setFixedSize(600, 300)

    def make_figure(self, times=None, voltages=None):
        self.axes.set_xlabel('time [s]')
        self.axes.set_ylabel('voltage [V]')
        self.axes.plot(times, voltages)

class AnalogVoltageEditor(QtGui.QDialog):
    sequence_parameters = {}
    def __init__(self, channel, sequence, config, reactor=None, cxn=None, parent=None):
        super(AnalogVoltageEditor, self).__init__(parent)
        self.channel = str(channel)
        self.sequence = sequence
        self.ramp_maker = RampMaker
        self.config = config
        self.reactor = reactor
        self.cxn = cxn

        self.loading = False
        self.connect()
   
    @inlineCallbacks
    def connect(self):
        if self.cxn is None:
            self.cxn = connection()  
            yield self.cxn.connect()
        self.context = yield self.cxn.context()
#        yield self.get_sequence_parameters()
        yield self.populate()
        self.connect_signals()

    @inlineCallbacks
    def populate(self):
        self.setWindowTitle(self.channel)

        self.canvas = MplCanvas()
        self.nav = NavigationToolbar(self.canvas, self)
        self.ramp_table = RampTable(self.ramp_maker)
        self.ramp_scroll = QtGui.QScrollArea()
        self.buttons = QtGui.QDialogButtonBox(QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Cancel, QtCore.Qt.Horizontal, self)

        self.ramp_scroll.setWidget(self.ramp_table)
        self.ramp_scroll.setFixedHeight(self.ramp_table.height()+self.ramp_scroll.horizontalScrollBar().height()-10)
        self.ramp_scroll.setWidgetResizable(True)
        self.buttons.button(QtGui.QDialogButtonBox.Ok).setDefault(False)
        
        self.layout = QtGui.QGridLayout()
        self.layout.setSpacing(0)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        self.layout.addWidget(self.nav)
        self.layout.addWidget(self.canvas)
        self.layout.addWidget(self.ramp_scroll)
        self.layout.addWidget(self.buttons)

        self.setLayout(self.layout)
       
        width = self.canvas.width()
        height = self.nav.height() + self.canvas.height() + self.ramp_scroll.height() + 20
        self.setFixedSize(width, height)
        yield self.set_columns()
        yield self.replot()

    @inlineCallbacks
    def connect_signals(self):
        # pyqt signals
        for c in self.ramp_table.cols:
            c.ramp_select.currentIndexChanged.connect(self.replot)
            for pw in c.parameter_widgets.values():
                for pb in pw.pboxes.values():
                    pb.returnPressed.connect(self.replot)
        
        for i, c in enumerate(self.ramp_table.cols):
            c.add.clicked.connect(self.add_column(i))
            c.dlt.clicked.connect(self.dlt_column(i))

            c.zero_button.clicked.connect(self.zero_column(i))
            c.prev_button.clicked.connect(self.prev_column(i))
            c.next_button.clicked.connect(self.next_column(i))
#            c.all_zero.clicked.connect(self.all_zero(i))

        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        # labrad signals
        conductor = yield self.cxn.get_server(self.config.conductor_servername)
        yield conductor.signal__parameters_updated(self.config.conductor_update_id)
        yield conductor.addListener(listener=self.receive_parameters, source=None, ID=self.config.conductor_update_id)

    @inlineCallbacks
    def get_sequence_parameters(self):
        conductor = yield self.cxn.get_server(self.config.conductor_servername)
        sp = yield conductor.set_sequence_parameters()
        self.sequence_parameters = json.loads(sp)
    
    @inlineCallbacks
    def receive_parameters(self, c, signal):
        yield self.replot()

    @inlineCallbacks
    def set_columns(self):
        self.loading = True
        for c in self.ramp_table.cols:
            c.hide()

        for s, c in zip(self.sequence[self.channel], self.ramp_table.cols):
            ramp_type = s['type']
            c.show()
            c.ramp_select.setCurrentIndex(c.ramp_select.findText(ramp_type))
	    for k in c.parameter_widgets[ramp_type].pboxes.keys():
                c.parameter_widgets[ramp_type].pboxes[k].display(s[k])
                
        self.loading = False
        yield self.replot()

    def add_column(self, i):
        def ac():
            sequence = self.get_sequence()
	    for c in sequence.keys():
                sequence[c].insert(i, sequence[c][i])

            scroll_position = self.ramp_scroll.horizontalScrollBar().value()
            self.set_sequence(sequence)
            self.ramp_scroll.horizontalScrollBar().setValue(scroll_position)
        return ac

    def dlt_column(self, i):
        def dc():
            sequence = self.get_sequence()
	    for c in sequence.keys():
                sequence[c].pop(i)

            scroll_position = self.ramp_scroll.horizontalScrollBar().value()
            self.set_sequence(sequence)
            self.ramp_scroll.horizontalScrollBar().setValue(scroll_position)
        return dc

    def zero_column(self, i):
        def zc():
            sequence = self.get_sequence()
            dt = sequence[self.channel][i]['dt']
            sequence[self.channel][i] = {'dt': dt, 'type': 's', 'vf': 0.0}
            
            scroll_position = self.ramp_scroll.horizontalScrollBar().value()
            self.set_sequence(sequence)
            self.ramp_scroll.horizontalScrollBar().setValue(scroll_position)
        return zc

    def prev_column(self, i):
        def pc():
            sequence = self.get_sequence()
            if i > 0:
                dt = sequence[self.channel][i]['dt']
                sequence[self.channel][i] = deepcopy(sequence[self.channel][i-1])
                sequence[self.channel][i]['dt'] = dt

            scroll_position = self.ramp_scroll.horizontalScrollBar().value()
            self.set_sequence(sequence)
            self.ramp_scroll.horizontalScrollBar().setValue(scroll_position)
        return pc

    def next_column(self, i):
        def nc():
            sequence = self.get_sequence()
            if i < len(sequence[self.channel]) - 1:
                dt = sequence[self.channel][i]['dt']
		sequence[self.channel][i] = deepcopy(sequence[self.channel][i+1])
                sequence[self.channel][i]['dt'] = dt

            scroll_position = self.ramp_scroll.horizontalScrollBar().value()
            self.set_sequence(sequence)
            self.ramp_scroll.horizontalScrollBar().setValue(scroll_position)
        return nc

#    def all_zero(self, i):
#        def az():
#            sequence = self.get_sequence()
#            for i in range(0, len(sequence[self.channel])):
#                dt = sequence[self.channel][i]['dt']
#                sequence[self.channel][i] = {'dt': dt, 'type': 's', 'vf': 0.0}
#                i += 1
#            self.set_sequence(sequence)
#        return az

    def set_sequence(self, sequence):
        self.sequence = sequence
        self.set_columns()

    @inlineCallbacks
    def get_plottable_sequence(self):
        sequence = self.ramp_table.get_channel_sequence()
        parameters = {'sequencer': get_sequence_parameters(sequence)}
        parameters_json = json.dumps(parameters)
        conductor = yield self.cxn.get_server(self.config.conductor_servername)
        pv_json = yield conductor.get_parameter_values(parameters_json, True)
        parameter_values = json.loads(pv_json)['sequencer']
        plottable_sequence = substitute_sequence_parameters(sequence, parameter_values)
        returnValue(self.ramp_maker(plottable_sequence).get_plottable())

    def get_sequence(self):
        channel_sequence = self.ramp_table.get_channel_sequence()
        self.sequence.update({self.channel: channel_sequence})
        return self.sequence

    @inlineCallbacks
    def replot(self, c=None):
        if not self.loading:
            T, V = yield self.get_plottable_sequence()
            self.canvas.make_figure(T, V)
            self.canvas.draw()

    def getEditedSequence(self):
        return self.get_sequence()

    def keyPressEvent(self, c):
        if QtGui.QApplication.keyboardModifiers() == QtCore.Qt.ControlModifier:
            if c.key() == QtCore.Qt.Key_Return:
                self.buttons.accepted.emit()
            if c.key() == QtCore.Qt.Key_Q:
                self.buttons.rejected.emit()
        else:
            QtGui.QWidget().keyPressEvent(c)

class FakeConfig(object):
    def __init__(self):
        self.conductor_servername = 'yesr20_conductor'
        self.conductor_update_id = 461349

if __name__ == '__main__':
    SEQUENCE = {'a': [{'type': 'sexp', 'dt': 1.0, 'vi': 2.0, 'vf': 5, 'tau': .5, 'pts': 5}, 
                      {'type': 'exp', 'dt': 1.0, 'vf': 0, 'tau': -.5, 'pts': 5}]}
    a = QtGui.QApplication([])
    import qt4reactor 
    qt4reactor.install()
    from twisted.internet import reactor
    from okfpga.sequencer.analog_ramps import RampMaker
    widget = RampTable(RampMaker)
    widget = AnalogVoltageEditor('a', sequence, RampMaker, FakeConfig(), reactor)
    widget.show()
    reactor.run()
