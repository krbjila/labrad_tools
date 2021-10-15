import json
import numpy as np
import sys

import collections
import variables_config

from PyQt4 import QtGui, QtCore, Qt
from PyQt4.QtCore import pyqtSignal
from twisted.internet.defer import inlineCallbacks
from twisted.internet.task import LoopingCall

sys.path.append('../../client_tools')
from connection import connection
from widgets import NeatSpinBox

class ParameterRow(QtGui.QWidget):
    def __init__(self, configuration):
        QtGui.QDialog.__init__(self)
        self.loadControlConfiguration(configuration)
        self.populateGUI()

    def loadControlConfiguration(self, configuration):
        for key, value in configuration.__dict__.items():
            setattr(self, key, value)
    
    def populateGUI(self):
        self.nameBox = QtGui.QLineEdit()
        self.nameBox.setFixedSize(self.boxWidth, self.boxHeight)
        self.valueBox = NeatSpinBox()
        self.valueBox.setFixedSize(self.boxWidth, self.boxHeight)
        self.valueBox.setValidator(QtGui.QDoubleValidator())

        self.layout = QtGui.QHBoxLayout()
        self.layout.addWidget(self.nameBox)
        self.layout.addWidget(self.valueBox)
        self.layout.setSpacing(0)
        self.layout.setContentsMargins(0, 0, 10, 0)

        self.setLayout(self.layout)

class ParameterControl(QtGui.QGroupBox):
    hasNewValue = False
    free = True

    def __init__(self, configuration, reactor, cxn=None):
        QtGui.QDialog.__init__(self)
        self.reactor = reactor
        self.cxn = cxn
        self.loadControlConfiguration(configuration)
        self.connected = False
        self.layout = QtGui.QVBoxLayout()
        self.reconnect = LoopingCall(self.connect)
        self.reconnect.start(1.0)

    def loadControlConfiguration(self, configuration):
        self.configuration = configuration
        for key, value in configuration.__dict__.items():
            setattr(self, key, value)

    @inlineCallbacks
    def connect(self):
        if not self.connected:
            try:
                self.connected = True
                self.cxn = connection()
                yield self.cxn.connect()
                self.context = yield self.cxn.context()
                self.server = yield self.cxn.get_server(self.servername)
                yield self.populateGUI()
                yield self.connectSignals()
            except Exception as e:
                self.setDisabled(True)
                self.connected = False
                print("Could not connect: {}".format(e))

    @inlineCallbacks
    def getServerConfiguratiom(self):
        yield None

    @inlineCallbacks
    def populateGUI(self):
        # added KM 08/28/17
        # initialize default variables and values from variables_config.py
        self.setDisabled(True)
        
        default_variables = variables_config.variables_dict

        # Gets variables which have been added to conductor but aren't stored in default_variables
        try:
            parameters = yield self.server.get_parameter_values()
            default_variables_dict = json.loads(parameters)["sequencer"]
            new_variables = [[k, v] for k,v in default_variables_dict.items() if len(k) > 0 and k[0] == '*' and [k, v] not in default_variables]
            default_variables += new_variables

            self.numRows = len(default_variables) + 1

            self.parameterRows = [ParameterRow(self.configuration) for i in range(self.numRows)]

            while self.layout.count():
                child = self.layout.takeAt(0)
                if child.widget() is not None:
                    child.widget().deleteLater()

            for pr in self.parameterRows:
                self.layout.addWidget(pr)
            self.layout.setSpacing(1)
            self.layout.setContentsMargins(0, 1, 0, 0)
            
            
            for i in range(len(default_variables)):
                self.parameterRows[i].nameBox.setText(default_variables[i][0])
                self.parameterRows[i].valueBox.display(default_variables[i][1])
                i += 1
            
            # Read in parameter values from LabRAD
            self.do_update()

            self.setFixedSize(2*(self.boxWidth+2), self.numRows*(self.boxHeight+2))
            self.setLayout(self.layout)

            self.setDisabled(False)
        except Exception as e:
            self.onDisconect()
            print("Could not populate GUI: {}".format(e))

    @inlineCallbacks
    def connectSignals(self):
        try:
            yield self.server.signal__parameters_updated(self.update_id)
            yield self.server.addListener(listener=self.receive_update, source=None, ID=self.update_id)
            yield self.cxn.add_on_disconnect(self.servername, self.onDisconect)

            for pr in self.parameterRows:
                pr.nameBox.returnPressed.connect(self.do_update)
                pr.valueBox.returnPressed.connect(self.writeValue(pr))

                pr.nameBox.returnPressed.connect(self.appendToRows)
                pr.valueBox.returnPressed.connect(self.appendToRows)
        except Exception as e:
            self.onDisconect()
            print("Could not connect signals: {}".format(e))

    def appendToRows(self):
        arr = self.parameterRows
        if arr[-1].nameBox.text() != "" or arr[-1].valueBox.text() != "":
            arr.append(ParameterRow(self.configuration))

            # Connect signals
            arr[-1].nameBox.returnPressed.connect(self.do_update)
            arr[-1].valueBox.returnPressed.connect(self.writeValue(arr[-1]))
            arr[-1].nameBox.returnPressed.connect(self.appendToRows)
            arr[-1].valueBox.returnPressed.connect(self.appendToRows)

            self.layout.addWidget(arr[-1])
            self.setLayout(self.layout)

    
    @inlineCallbacks
    def receive_update(self, c, signal):
        if signal:
            try:
                yield self.do_update()
            except Exception as e:
                self.onDisconect()
                print("Could not receive update: {}".format(e))

    @inlineCallbacks
    def do_update(self):
        try:
            parameters_json = yield self.server.get_parameter_values()
            parameters = json.loads(parameters_json)[self.device]
            for pr in self.parameterRows:
                parameterName = str(pr.nameBox.text())
                if parameterName in parameters.keys():
                    pr.valueBox.display(parameters[parameterName])
        except Exception as e:
            self.onDisconect()
            print("Could not do update: {}".format(e))

    def writeValue(self, parameterRow):
        @inlineCallbacks
        def wv():
            try:
                name = str(parameterRow.nameBox.text())
                value = float(parameterRow.valueBox.value())
                if len(name) > 1 and name[0] != '*':
                    parameterRow.nameBox.setStyleSheet("background-color: red;")
                elif len(name) > 0:
                    parameterRow.nameBox.setStyleSheet("background-color: white;")
                    yield self.server.set_parameter_values(json.dumps({self.device: {name: value}}))
                    parameterRow.valueBox.display(value)
            except Exception as e:
                self.onDisconect()
                print("Could not write value: {}".format(e))
        return wv

    # There is some kind of subtlety with functions that are defined as
    # Qt slots (responses to a Qt signal). Had to redefine this function
    # to be able to call it directly in the code
    @inlineCallbacks
    def forceWriteValue(self, parameterRow):
        try:
            name = str(parameterRow.nameBox.text())
            value = float(parameterRow.valueBox.value())
            yield self.server.set_parameter_values(json.dumps({self.device: {name: value}}))
            parameterRow.valueBox.display(value)
        except Exception as e:
            self.onDisconect()
            print("Could not force write value: {}".format(e))

    def onDisconect(self):
        self.setDisabled(True)
        self.connected = False


    def closeEvent(self, x):
        self.reactor.stop()

class ControlConfig(object):
    def __init__(self):
        self.servername = 'conductor'
        self.update_id = 461028
        self.updateTime = 100 # [ms]
        self.boxWidth = 80
        self.boxHeight = 20
        self.numRows = 15
        self.device = 'sequencer'

if __name__ == '__main__':
    import sys
    a = QtGui.QApplication([])
    import qt4reactor
    qt4reactor.install()
    from twisted.internet import reactor
    widget = ParameterControl(ControlConfig(), reactor)
    widget.show()
    reactor.run()
