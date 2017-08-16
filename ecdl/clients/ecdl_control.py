import json
import numpy as np
import sys

from PyQt4 import QtGui, QtCore, Qt
from PyQt4.QtCore import pyqtSignal
from twisted.internet.defer import inlineCallbacks

sys.path.append('../../client_tools')
from connection import connection
from widgets import SuperSpinBox

class ParameterLabel(QtGui.QLabel):
    clicked = pyqtSignal()
    def mousePressEvent(self, x):
        self.clicked.emit()

class ECDLControl(QtGui.QGroupBox):
    def __init__(self, config, reactor, cxn=None):
        QtGui.QDialog.__init__(self)
        self.reactor = reactor
        self.cxn = cxn 
        self.load_config(config)
        self.connect()

    def load_config(self, config=None):
        if type(config).__name__ == 'str':
            config = __import__(config).ControlConfig()
        if config is not None:
            self.config = config
        for key, value in self.config.__dict__.items():
            setattr(self, key, value)

    @inlineCallbacks
    def connect(self):
        if self.cxn is None:
            self.cxn = connection()
            yield self.cxn.connect()
        self.context = yield self.cxn.context()
        yield self.select_device()
        self.populateGUI()
        yield self.connectSignals()
        yield self.requestValues()

    @inlineCallbacks
    def select_device(self):
        server = yield self.cxn.get_server(self.servername)
        config = yield server.select_device(self.name)
        for key, value in json.loads(config).items():
            setattr(self, key, value)
        self.load_config()
    
    def populateGUI(self):
        self.state_button = QtGui.QPushButton()
        self.state_button.setCheckable(1)
        
        self.piezo_voltage_box = SuperSpinBox(self.piezo_voltage_range, 
                                          self.piezo_voltage_display_units, 
                                          self.piezo_voltage_digits)
        self.piezo_voltage_box.setFixedWidth(self.spinbox_width)
        self.piezo_voltage_box.display(0)
        
        self.diode_current_box = SuperSpinBox(self.diode_current_range, 
                                          self.diode_current_display_units, 
                                          self.diode_current_digits)
        self.diode_current_box.setFixedWidth(self.spinbox_width)
        self.diode_current_box.display(0)

        self.layout = QtGui.QGridLayout()
        
        row = 0
        self.layout.addWidget(QtGui.QLabel('<b>'+self.name+'</b>'), 
                              0, 0, 1, 1, QtCore.Qt.AlignHCenter)
        if 'state' in self.update_parameters:
            self.layout.addWidget(self.state_button, 0, 1)
        else:
            self.layout.addWidget(QtGui.QLabel('always on'), 
                                  0, 0, 1, 1, QtCore.Qt.AlignHCenter)
        if 'piezo_voltage' in self.update_parameters:
            row += 1
            self.piezo_voltage_label = ParameterLabel('Piezo Voltage: ')
            self.layout.addWidget(self.piezo_voltage_label, 
                                  row, 0, 1, 1, QtCore.Qt.AlignRight)
            self.layout.addWidget(self.piezo_voltage_box, row, 1)
        if 'diode_current' in self.update_parameters:
            row += 1
            self.diode_current_label = ParameterLabel('Diode Current: ')
            self.layout.addWidget(self.diode_current_label, 
                                  row, 0, 1, 1, QtCore.Qt.AlignRight)
            self.layout.addWidget(self.diode_current_box, row, 1)

        self.setWindowTitle(self.name + '_control')
        self.setLayout(self.layout)
        self.setFixedSize(120 + self.spinbox_width, 100)

    @inlineCallbacks
    def connectSignals(self):
        self.hasNewState = False
        self.hasNewPiezoVoltage = False
        self.hasNewDiodeCurrent = False
        server = yield self.cxn.get_server(self.servername)
        yield server.signal__update(self.update_id)
        yield server.addListener(listener=self.receive_update, source=None, 
                                 ID=self.update_id)
        yield self.cxn.add_on_connect(self.servername, self.reinitialize)
        yield self.cxn.add_on_disconnect(self.servername, self.disable)

        self.state_button.released.connect(self.onNewState)
        self.piezo_voltage_box.returnPressed.connect(self.onNewPiezoVoltage)
        self.diode_current_box.returnPressed.connect(self.onNewDiodeCurrent)

        if 'piezo_voltage' in self.update_parameters:
            self.piezo_voltage_label.clicked.connect(self.requestValues)
        if 'diode_current' in self.update_parameters:
            self.diode_current_label.clicked.connect(self.requestValues)
        
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.writeValues)
        self.timer.start(self.update_time)

    @inlineCallbacks
    def requestValues(self, c=None):
        server = yield self.cxn.get_server(self.servername)
        for parameter in self.update_parameters:
            yield getattr(server, parameter)()
 
    def receive_update(self, c, signal):
        signal = json.loads(signal)
        for name, d in signal.items():
            self.free = False
            if name == self.name:
                if 'state' in self.update_parameters:
                    if d['state']:
                        self.state_button.setChecked(1)
                        self.state_button.setText('On')
                    else:
                        self.state_button.setChecked(0)
                        self.state_button.setText('Off')
                
                if 'piezo_voltage' in self.update_parameters:
                    self.piezo_voltage_box.display(d['piezo_voltage'])
    
                if 'diode_current' in self.update_parameters:
                    self.diode_current_box.display(d['diode_current'])
        self.free = True
    
    @inlineCallbacks
    def onNewState(self):
        if self.free:
            server = yield self.cxn.get_server(self.servername)
            is_on = yield server.state()
            print 'state', is_on
            if is_on:
                yield server.shutdown()
            else:
                yield server.warmup()

    def onNewPiezoVoltage(self):
        if self.free:
            self.hasNewPiezoVoltage = True
   
    def onNewDiodeCurrent(self):
        if self.free:
            self.hasNewDiodeCurrent = True

    @inlineCallbacks
    def writeValues(self):
        if self.hasNewPiezoVoltage:
            server = yield self.cxn.get_server(self.servername)
            yield server.piezo_voltage(self.piezo_voltage_box.value())
            self.hasNewPiezoVoltage = False
        elif self.hasNewDiodeCurrent:
            server = yield self.cxn.get_server(self.servername)
            yield server.diode_current(self.diode_current_box.value())
            self.hasNewDiodeCurrent = False
           
    def reinitialize(self):
        self.setDisabled(False)

    def disable(self):
        self.setDisabled(True)

    def closeEvent(self, x):
        self.reactor.stop()

