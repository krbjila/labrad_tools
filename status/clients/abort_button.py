import json
import time
import numpy as np
import os
import sys

import client_config

from PyQt4.QtGui import *
from PyQt4.QtCore import *
from twisted.internet.defer import inlineCallbacks

from pathlib import Path
sys.path.append([str(i) for i in Path(__file__).parents if str(i).endswith("labrad_tools")][0])
from client_tools.connection import connection

SEP = os.path.sep

# Runs the abort button and communicates with Labrad servers
class AbortButton(QWidget):
    (x, y) = (client_config.abort['x'], client_config.abort['y'])

    def __init__(self, reactor, parent=None):
        super(AbortButton, self).__init__(parent)
        self.reactor = reactor
        self.setMinimumWidth(self.x)
        self.setMinimumHeight(self.y)
        self.ID_started = 22222
        self.ID_stopped = 22223
 
        # layout the GUI
        self.setupLayout()

        # start connections with LABRAD
        self.initialize()
    
    @inlineCallbacks
    def initialize(self):
        try:
            self.cxn = connection()
            yield self.cxn.connect()
            self.server = yield self.cxn.get_server('conductor')
        except:
            self.button.setEnabled(False)
        self.button.clicked.connect(self.abort)

    @inlineCallbacks
    def abort(self, c):
        self.button.setEnabled(False)
        success = yield self.server.abort_experiment()
        if success:
            self.button.setEnabled(True)

    # Lays out the widget
    def setupLayout(self):
        self.setWindowTitle('Status Widget')
        #create a vertical layout
        layout = QVBoxLayout()
        self.button = QPushButton("Abort!", self)
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
    widget = AbortButton(reactor)
    widget.show()
    reactor.run()
