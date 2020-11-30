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

from devices.lib.ad5791_ramps import RampMaker

from copy import deepcopy

def zero_sequence(dt):
    return {'dt': dt, 'type': 's', 'vf': 0}

class Combo(QtGui.QComboBox):
    def __init__(self, *args):
        super(Combo, self).__init__()
        self.addItem('0: Default')
        self.lookup = {'0': 0}

    def updatePresets(self, presets):
        self.presets = presets
        self.presets_sorted = [(key, self.presets[key]) for key in sorted(self.presets.keys())]

        self.clear()
        self.lookup = {}
        for i in range(len(self.presets_sorted)):
            (x,y) = self.presets_sorted[i]
            self.addItem(str(x) + ': ' + y['description'])
            self.lookup[str(x)] = i
        self.setCurrentIndex(0)

    def display(self, value):
        v = str(int(value))

        try:
            self.setCurrentIndex(self.lookup[v])
        except:
            self.setCurrentIndex(0)

    def value(self):
        return self.presets_sorted[int(self.currentIndex())][0]


class ParameterWidget(QtGui.QWidget):
    def __init__(self, ramp_type, ramp):
        """
        parameters is [(parameter_label, (range, suffixes, num_decimals)),]
        """
        super(ParameterWidget, self).__init__(None)
        self.ramp_type = ramp_type
        self.parameters = ramp.required_parameters
        self.populate()

    def populate(self):
        self.layout = QtGui.QGridLayout()
        self.pboxes = {}
        if self.ramp_type is 'sub':
            r, s, n = dict(self.parameters)['dt']
            label, self.pboxes['dt'] = self.make_pbox('dt', r, s, n)
            self.subbox = QtGui.QTextEdit()
            self.subbox.setLineWrapMode(0)
            self.subbox.setFixedWidth(90+30+2)
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
                self.layout.addWidget(QtGui.QLabel(label), i, 0)
                self.layout.addWidget(self.pboxes[p], i, 1)
        self.setFixedWidth(90+30+4)

        self.layout.setSpacing(0)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(QtGui.QFrame())
        self.setLayout(self.layout)

    def make_pbox(self, p, r, s, n):
        if p == 'vi': 
            pbox = Combo()
            pbox.display(0)
        elif p == 'vf':
            pbox = Combo()
            pbox.display(0)
        else:
            pbox = SuperSpinBox(r, s, n)
            pbox.display(1)

        if p == 'dt':
            pbox.setDisabled(True)
        
        label = QtGui.QLabel(p+': ')
        label.setFixedWidth(30)
        label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        pbox.setFixedWidth(90)
        pbox.setFixedHeight(20)
        return p, pbox

class RampColumn(QtGui.QGroupBox):
    def __init__(self, RampMaker):
        super(RampColumn, self).__init__(None)
        self.ramp_maker = RampMaker
        self.presets = {}
        self.populate()

    def populate(self):
        self.add = QtGui.QWidget()
        self.dlt = QtGui.QWidget()
        # self.add = QtGui.QPushButton('+')
        # self.dlt = QtGui.QPushButton('-')
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

        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.add, 0, 0)
        self.layout.addWidget(self.dlt, 0, 1)
        self.layout.addWidget(self.ramp_select, 0, 2)
        self.layout.addWidget(self.stack, 1, 0, 1, 3)

        self.layout.addWidget(self.zero_button, 2, 2, 1, 2)
        self.layout.addWidget(self.prev_button, 3, 2, 1, 2)
        self.layout.addWidget(self.next_button, 4, 2, 1, 2)

        self.zero_button.setFixedSize(90, 20)
        self.prev_button.setFixedSize(90, 20)
        self.next_button.setFixedSize(90, 20)

        self.setLayout(self.layout)
        self.layout.setSpacing(0)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.add.setFixedSize(16, 20) # w, h
        self.dlt.setFixedSize(16, 20) # w, h
        self.ramp_select.setFixedWidth(90)
        self.ramp_select.setFixedHeight(20)
        self.setFixedWidth(30+120+4)

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

    def updatePresets(self, presets):
        self.presets = presets
        for p in self.parameter_widgets.values():        
            ps = p.pboxes
            for k in ps.keys():
                if k == 'vi' or k == 'vf':
                    ps[k].updatePresets(self.presets)

    def get_ramp(self):
        ramp_type = str(self.ramp_select.currentText())
        ramp = {'type': str(self.ramp_select.currentText())}
        if ramp['type'] != 'sub':
            ramp.update({k: b.value() for k, b in self.stack.currentWidget().pboxes.items()})
        else:
            ramp.update({'seq': eval('['+str(self.stack.currentWidget().subbox.toPlainText())+']')})
        return ramp

class RampTable(QtGui.QWidget):
    def __init__(self, RampMaker, sequence_length):
        QtGui.QDialog.__init__(self)
        self.ramp_maker = RampMaker
        self.sequence_length = sequence_length
        self.populate()

    def populate(self):
        self.cols = [RampColumn(self.ramp_maker) for i in range(self.sequence_length)]
        self.layout = QtGui.QHBoxLayout()
        for c in self.cols:
            self.layout.addWidget(c)
        self.layout.addWidget(QtGui.QFrame())
        self.layout.setSpacing(2)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.setLayout(self.layout)

    def get_sequence(self):
        return [c.get_ramp() for c in self.cols]

class MplCanvas(FigureCanvas):
    def __init__(self, channel_list):
        self.fig = Figure()
        self.axes = self.fig.add_subplot(111)

        self.channel_list = channel_list

        self.fig.set_tight_layout(True)

        FigureCanvas.__init__(self, self.fig)
        self.setFixedSize(600, 300)

    def clear(self):
        self.axes.clear()

    def legend(self):
        self.axes.legend()

    def make_figure(self, waveforms):
        self.axes.set_xlabel('time [s]')
        self.axes.set_ylabel('voltage [V]')

        for x in self.channel_list:
            (T, V) = waveforms[x]
            self.axes.plot(T, V, label=x)

        self.axes.legend()


class ElectrodeEditor(QtGui.QDialog):
    sequence_parameters = {}
    def __init__(self, channels, sequence, electrode_sequence, config, reactor=None, cxn=None, parent=None):
        super(ElectrodeEditor, self).__init__(parent)
        self.channels = channels
        self.sequence = sequence

        self.ramp_maker = RampMaker
        self.config = config
        self.reactor = reactor
        self.cxn = cxn

        self.lookup = self.generateChannelLookup(self.channels)

        self.electrode_sequence = self.check_electrode_sequence(electrode_sequence)
        self.sequence_length = len(electrode_sequence)
        self.presets = {}

        self.loading = False
        self.connect()

    def generateChannelLookup(self, channels):
        lookup = {}
        for i, nl in enumerate(sorted(self.channels, key=lambda nl: nl.split('@')[1])):
            lookup[self.config.electrode_channel_map[i]] = nl
        return lookup

    def check_electrode_sequence(self, electrode_sequence):
        dummy = self.sequence.keys()[0]
        dummy_seq = self.sequence[dummy]

        if len(electrode_sequence) != len(dummy_seq):
            electrode_sequence = []
            for x in dummy_seq:
                v = deepcopy(zero_sequence(x['dt']))
                electrode_sequence.append(v)
        return electrode_sequence

    @inlineCallbacks
    def connect(self):
        if self.cxn is None:
            self.cxn = connection()  
            yield self.cxn.connect()
        self.context = yield self.cxn.context()
#        yield self.get_sequence_parameters()
        self.populate()
        yield self.connect_signals()
        yield self.update_presets()

    def populate(self):
        self.setWindowTitle("Electrode control")

        self.canvas = MplCanvas(self.config.electrode_channel_map)
        self.nav = NavigationToolbar(self.canvas, self)
        self.ramp_table = RampTable(self.ramp_maker, self.sequence_length)
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

    @inlineCallbacks
    def connect_signals(self):
        # pyqt signals
        for c in self.ramp_table.cols:
            c.ramp_select.currentIndexChanged.connect(self.replot)
            for pw in c.parameter_widgets.values():
                for key, pb in pw.pboxes.items():
                    if key == 'vi' or key == 'vf':
                        pb.currentIndexChanged.connect(self.replot)
                    else:
                        pb.returnPressed.connect(self.replot)
        
        for i, c in enumerate(self.ramp_table.cols):
            # c.add.clicked.connect(self.add_column(i))
            # c.dlt.clicked.connect(self.dlt_column(i))

            c.zero_button.clicked.connect(self.zero_column(i))
            c.prev_button.clicked.connect(self.prev_column(i))
            c.next_button.clicked.connect(self.next_column(i))

        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        self.electrode = yield self.cxn.get_server(self.config.electrode_servername)
        yield self.electrode.signal__presets_changed(self.config.electrode_update_id)
        yield self.electrode.addListener(listener=self._update_presets, source=None, ID=self.config.electrode_update_id)

        # labrad signals
        self.conductor = yield self.cxn.get_server(self.config.conductor_servername)
        yield self.conductor.signal__parameters_updated(self.config.conductor_update_id)
        yield self.conductor.addListener(listener=self.receive_parameters, source=None, ID=self.config.conductor_update_id)

    @inlineCallbacks
    def get_electrode_presets(self):
        s = yield self.electrode.get_presets()
        s = json.loads(s)

        presets = {}
        for x in s:
            idn = x.pop('id')
            presets[idn] = x
        self.presets = presets

    def _update_presets(self, c, x):
        self.update_presets()

    @inlineCallbacks
    def update_presets(self):
        self.loading = True

        yield self.get_electrode_presets()

        for c in self.ramp_table.cols:
            c.updatePresets(self.presets)

        self.loading = False

        yield self.set_columns()

    @inlineCallbacks
    def get_sequence_parameters(self):
        sp = yield self.conductor.set_sequence_parameters()
        self.sequence_parameters = json.loads(sp)
    
    @inlineCallbacks
    def receive_parameters(self, c, signal):
        yield self.replot()

    @inlineCallbacks
    def set_columns(self):
        self.loading = True

        for s, c in zip(self.electrode_sequence, self.ramp_table.cols):
            ramp_type = s['type']
            c.ramp_select.setCurrentIndex(c.ramp_select.findText(ramp_type))
        
            for k in c.parameter_widgets[ramp_type].pboxes.keys():
                c.parameter_widgets[ramp_type].pboxes[k].display(s[k])
                
        self.loading = False
        yield self.replot()

    def zero_column(self, i):

        # QAbstractButton.clicked() sends a bool (for whether the button is checked or not)
        # This will cause an error as zc is then called with an extra argument
        # Just put *args and ignore them to catch this
        @inlineCallbacks
        def zc(*args):
            self.electrode_sequence = self.getElectrodeSequence()
            dt = self.electrode_sequence[i]['dt']
            self.electrode_sequence[i] = zero_sequence(dt)
            yield self.set_columns()
        
        return zc

    def prev_column(self, i):

        # See comment on zc()
        @inlineCallbacks
        def pc(*args):
            self.electrode_sequence = self.getElectrodeSequence()

            if i > 0:
                dt = self.electrode_sequence[i]['dt']
                self.electrode_sequence[i] = deepcopy(self.electrode_sequence[i-1])
                self.electrode_sequence[i]['dt'] = dt
                yield self.set_columns()
        
        return pc

    def next_column(self, i):
        
        # See comment on zc()
        @inlineCallbacks
        def nc(*args):
            self.electrode_sequence = self.getElectrodeSequence()

            if i < len(self.electrode_sequence) - 1:
                dt = self.electrode_sequence[i]['dt']
                self.electrode_sequence[i] = deepcopy(self.electrode_sequence[i+1])
                self.electrode_sequence[i]['dt'] = dt
                yield self.set_columns()
        
        return nc

    def parseElectrodesSequence(self, electrode_sequence):
        sequence = {}
        for x in self.config.electrode_channel_map:
            s = []
            for step in electrode_sequence:
                seq = deepcopy(step)
                vf = self.presets[int(step['vf'])]['values'][x]
                seq['vf'] = vf
                if 'vi' in step:
                    vi = self.presets[int(step['vi'])]['values'][x]
                    seq['vi'] = vi
                s.append(seq)
            sequence[x] = s
        return sequence

    @inlineCallbacks
    def get_plottable_sequence(self):
        sequence = self.ramp_table.get_sequence()
        parameters_json = json.dumps({'sequencer': get_sequence_parameters(sequence)})
        pv_json = yield self.conductor.get_parameter_values(parameters_json, True)
        parameter_values = json.loads(pv_json)['sequencer']
        sequence = substitute_sequence_parameters(sequence, parameter_values)

        fixed_sequence = self.parseElectrodesSequence(sequence)
        returnValue({key: self.ramp_maker(val).get_plottable() for key, val in fixed_sequence.items()})
    
    def get_sequence(self):
        electrode_sequence = self.ramp_table.get_sequence()
        fixed_sequence = self.parseElectrodesSequence(electrode_sequence)

        for k, v in fixed_sequence.items():
            self.sequence.update({self.lookup[k]: v})
        return self.sequence

    @inlineCallbacks
    def replot(self, c=None):
        if not self.loading:
            self.canvas.clear()

            # Update the electrode sequence
            self.electrode_sequence = self.getElectrodeSequence()

            seq = yield self.get_plottable_sequence()
            self.canvas.make_figure(seq)
            # for key, val in seq.items():
            #     (T, V) = val
            #     self.canvas.make_figure(T, V, key)
            self.canvas.draw()
        self.canvas.legend()

    def getEditedSequence(self):
        return self.get_sequence()

    def getElectrodeSequence(self):
        return self.ramp_table.get_sequence()

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
    widget = ElectrodeEditor('a', sequence, RampMaker, FakeConfig(), reactor)
    widget.show()
    reactor.run()
