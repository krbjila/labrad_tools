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

class ArduinoClient(QtGui.QWidget):
    def __init__(self, reactor, parent=None):
        super(ArduinoClient, self).__init__(parent)
        self.reactor = reactor
        self.alive = True
        self.state = -1

        # define IDs for LABRAD signals
        self.ID_case = 6969
        self.ID_start = 6970
        self.ID_stop = 6971
        self.ID_kill = 6972
        
        # layout the GUI
        self.setupLayout()

        # start connections with LABRAD
        self.initialize()
    
    @inlineCallbacks
    def initialize(self):
        yield self.connect()

    @inlineCallbacks
    def connect(self):
        # connect to LABRAD
        # needs Arduino server and Conductor running
        from labrad.wrappers import connectAsync
        self.cxn = yield connectAsync(name = 'ArduinoControl')
        self.server = yield self.cxn.krbjila_arduino

        # open connection with Arduino device
        devices = yield self.server.get_interface_list()
        for device in devices:
            if device[0:-1] == '/dev/ttyACM':
                yield self.server.select_interface(device)
                self.device = device
        try:
            yield self.server.reset_input_buffer()
        except:
            raise Exception('Arduino device not found.')

        # Connect to LABRAD signal from ArduinoServer.
        # This is the signal that is set and displayed by this widget
        # upon a state change of the Arduino.
        # This signal is also received by the E8257D/enable.py script
        # and determines what the synth does.
        yield self.server.signal__case(self.ID_case)
        yield self.server.addListener(listener = self.displaySignal, source = None, ID = self.ID_case)
        
        # Connect to experiment_started signal from Conductor
        yield self.cxn.conductor.signal__experiment_started(self.ID_start)
        yield self.cxn.conductor.addListener(listener = self.started, source = None, ID = self.ID_start)

        # Connect to experiment_stopped signal from Conductor
        yield self.cxn.conductor.signal__experiment_stopped(self.ID_stop)
        yield self.cxn.conductor.addListener(listener = self.stopped, source = None, ID = self.ID_stop)

        # Connect to kill signal from ArduinoServer
        yield self.server.signal__kill(self.ID_kill)
        yield self.server.addListener(listener = self.onKillSignal, source = None, ID = self.ID_kill)

    def onKillSignal(self, cntx, signal):
        if signal:
            self.alive = False

    # Runs when the client receives the experiment_started signal from Conductor.
    # Sets variables, writes a timestamp to the widget, and starts the loop()
    def started(self, cntx, signal):
        if signal:
            self.state = -1
        self.alive = True
        timestr = time.strftime("%H:%M:%S", time.localtime())
        self.textedit.append("started " + timestr)
        self.loop()

    # Runs when the client gets the experiment_stopped signal from Conductor.
    # Sets variables, ends the loop(), and prints timestamp to the widget.
    def stopped(self, cntx, signal):
        if signal and self.alive:
            self.alive = False
            timestr = time.strftime("%H:%M:%S", time.localtime())
            self.textedit.append("stopped " + timestr)
        else:
            self.alive = False

    # Lays out the widget
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

    # Writes state signal to widget
    def displaySignal(self, cntx, signal):
        self.textedit.append(signal)

    def closeEvent(self, x):
        #stop the reactor when closing the widget
        self.alive = False
        self.reactor.stop()

    # The main loop for checking the state of the Arduino.
    @inlineCallbacks
    def loop(self):
        from labrad import util
        while self.alive:
            # Check the serial port
            bytes_waiting = yield self.server.in_waiting()
            if bytes_waiting:
                newstate = yield self.server.read(1)
                if self.state != newstate:
                    # On state change, tell ArduinoServer to emit a signal
                    # that tells enable.py what it should do.
                    yield self.server.emit_advance_signal(str(newstate))
                    self.state = newstate
                yield self.server.reset_input_buffer()

# Starts the widget
if  __name__ == '__main__':
    a = QtGui.QApplication( [] )
    import qt4reactor
    qt4reactor.install()
    from twisted.internet import reactor
    widget = ArduinoClient(reactor)
    widget.show()
    reactor.run()
