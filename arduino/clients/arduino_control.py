import json
import time
import numpy as np
import os
import sys

sys.path.append('../../client_tools')

from PyQt4 import QtGui, QtCore, Qt
from PyQt4.QtCore import pyqtSignal 
from twisted.internet.defer import inlineCallbacks

SEP = os.path.sep

class ArduinoControl(QtGui.QWidget):
    def __init__(self, reactor, parent=None):
        super(ArduinoControl, self).__init__(parent)
        self.reactor = reactor
        self.alive = True
        self.state = -1
        self.ID_case = 6969
        self.ID_start = 6970
        self.ID_kill = 6971
        self.setupLayout()
        self.initialize()
    
    @inlineCallbacks
    def initialize(self):
        yield self.connect()
        yield self.loop()

    @inlineCallbacks
    def connect(self):
        from labrad.wrappers import connectAsync
        self.cxn = yield connectAsync(name = 'ArduinoControl')
        self.server = yield self.cxn.krbjila_arduino
        devices = yield self.server.get_interface_list()
        for device in devices:
            if device[0:-1] == '/dev/ttyACM':
                yield self.server.select_interface(device)
                self.device = device
        try:
            yield self.server.reset_input_buffer()
        except:
            raise Exception('Arduino device not found.')
        yield self.server.signal__case(self.ID_case)
        yield self.server.addListener(listener = self.displaySignal, source = None, ID = self.ID_case)
        
        yield self.cxn.conductor.signal__experiment_started(self.ID_start)
        yield self.cxn.conductor.addListener(listener = self.started, source = None, ID = self.ID_start)

        yield self.server.signal__kill(self.ID_kill)
        yield self.server.addListener(listener = self.onKillSignal, source = None, ID = self.ID_kill)

    def onKillSignal(self, cntx, signal):
        if signal:
            self.alive = False

    def started(self, cntx, signal):
        if signal:
            self.state = -1

    def setupLayout(self):
        #setup the layout and make all the widgets
        self.setWindowTitle('Arduino Widget')
        #create a horizontal layout
        layout = QtGui.QHBoxLayout()
        #create the text widget 
        self.textedit = QtGui.QTextEdit()
        self.textedit.setReadOnly(False)
        layout.addWidget(self.textedit)
        self.setLayout(layout)

    def displaySignal(self, cntx, signal):
        self.textedit.append(signal)

    def closeEvent(self, x):
        #stop the reactor when closing the widget
        self.alive = False
        self.reactor.stop()

    @inlineCallbacks
    def loop(self):
        from labrad import util
        while True:
            bytes_waiting = yield self.server.in_waiting()
            if bytes_waiting:
                newstate = yield self.server.read(1)
                if self.state != newstate:
                    yield self.server.emit_advance_signal(str(newstate))
                    self.state = newstate
                yield self.server.reset_input_buffer()
            if not self.alive:
                break

                

if  __name__ == '__main__':
    a = QtGui.QApplication( [] )
    import qt4reactor
    qt4reactor.install()
    from twisted.internet import reactor
    widget = ArduinoControl(reactor)
    widget.show()
    reactor.run()
