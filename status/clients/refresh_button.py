import json
import time
import numpy as np
import os
import sys

import client_config

sys.path.append('../../client_tools')
sys.path.append('../client_tools')

from PyQt4.QtGui import *
from PyQt4.QtCore import *
from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.internet.task import LoopingCall
from connection import connection

SEP = os.path.sep

# Runs the refresh button and communicates with Labrad servers
class RefreshButton(QWidget):
    (x, y) = (client_config.refresh['x'], client_config.refresh['y'])

    def __init__(self, reactor, parent=None):
        super(RefreshButton, self).__init__(parent)
        self.reactor = reactor
        self.setMinimumWidth(self.x)
        self.setMinimumHeight(self.y)
        self.ID_started = 22224
        self.ID_stopped = 22225
 
        # layout the GUI
        self.setupLayout()

        # start connections with LABRAD
        self.initialize()
    
    def initialize(self):
        self.connected = False
        self.reconnect = LoopingCall(self.connect)
        self.reconnect.start(1.0)

    @inlineCallbacks
    def connect(self):
        if not self.connected:
            try:
                self.cxn = connection()
                yield self.cxn.connect()
                self.server = yield self.cxn.get_server('conductor')
                self.button.clicked.connect(self.refresh_parameters)

                self.connected = True
            except:
                self.button.setEnabled(False)


    # Tell conductor to refresh parameters
    @inlineCallbacks
    def refresh_parameters(self, c):
        self.button.setEnabled(False)
        try:
            yield self.server.refresh_default_parameters()
            self.button.setEnabled(True)
        except Exception as e:
            self.connected = False


    # Lays out the widget
    def setupLayout(self):
        self.setWindowTitle('Status Widget')
        #create a vertical layout
        layout = QVBoxLayout()
        self.button = QPushButton("Refresh parameters", self)
        self.button.resize(self.x, self.y)
        layout.addWidget(self.button)

    def closeEvent(self, x):
        #stop the reactor when closing the widget
        self.alive = False
        self.reactor.stop()

# Starts the widget
if  __name__ == '__main__':
    a = QApplication( [] )
    import qt4reactor
    qt4reactor.install()
    from twisted.internet import reactor
    widget = RefreshButton(reactor)
    widget.show()
    reactor.run()
