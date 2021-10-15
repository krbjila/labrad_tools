import json
import time
import numpy as np
import os
import sys
from PyQt4 import QtGui, QtSvg

import client_config

sys.path.append('../../client_tools')
sys.path.append('../client_tools')

from PyQt4.QtGui import *
from PyQt4.QtCore import *
from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.internet.task import LoopingCall
from connection import connection

from abort_button import AbortButton
from refresh_button import RefreshButton

SEP = os.path.sep

WAIT_TIME = 3.0

# Indicator button widget
class Indicator(QWidget):
    RAD = client_config.widget['rad']

    # Initialize and set geometry
    def __init__(self, parent=None):
        super(QWidget, self).__init__(parent)
        self.setGeometry(0,0,3*self.RAD,3*self.RAD)
        self.setMinimumSize(QSize(3*self.RAD,3*self.RAD))
        self.coords = [1.5*self.RAD, 1.5*self.RAD]        
        self.color = QColor(client_config.widget['colorIdle'])
        self.warning_flag = 0
        self.eye = QtSvg.QSvgRenderer('eye.svg')

    # Resize when stretched
    def resizeEvent(self, event):
        self.coords = [0.5*event.size().width(), 0.5*event.size().height()]
        self.RAD = 0.75*min(self.coords)
        event.accept()

    # Repaint the indicator on event
    def paintEvent(self, event):
        # Start the painter
        painter = QPainter()
        painter.begin(self)
        painter.setRenderHint(QPainter.Antialiasing)
        # Set white backgrount
        painter.setBrush(Qt.white)
        painter.drawRect(event.rect())
        # Get radius of circle
        rad = self.RAD
        # Set no outline
        painter.setPen(Qt.white)
        # Setup the gradient
        gradient = QRadialGradient(QPointF(self.coords[0], self.coords[1]), rad)
        gradient.setColorAt(0, self.color)
        gradient.setColorAt(0.8, self.color)
        gradient.setColorAt(1, Qt.white)
        brush = QBrush(gradient)
        painter.setBrush(brush)
        # Draw the button
        if self.color != QColor(client_config.widget['colorOn']):
            painter.drawEllipse(QPoint(self.coords[0], self.coords[1]), rad, rad)
        else:
            top_left = QPoint(self.coords[0]-rad, self.coords[1]-rad)
            bottom_right = QPoint(self.coords[0]+rad, self.coords[1]+rad)
            self.eye.render(painter, QRectF(top_left, bottom_right))
        painter.end()

    def exptStarted(self):
        self.color = QColor(client_config.widget['colorOn'])
        self.update()

    def exptStopped(self):
        if self.warning_flag:
            self.color = QColor(client_config.widget['colorWarning'])
        else:
            self.color = QColor(client_config.widget['colorOff'])
        self.update()

    def labradServerError(self):
        self.color = QColor(client_config.widget['colorError'])
        self.update()

    def parameterRemoved(self):
        self.color = QColor(client_config.widget['colorWarning'])
        self.update()

    def parametersRefreshed(self):
        self.color = QColor(client_config.widget['colorOff'])
        self.update()


# Runs the indicator button and communicates with Labrad servers
class StatusClient(QWidget):
    RAD = client_config.widget['rad']
    exptStarted = pyqtSignal()
    exptStopped = pyqtSignal()
    labradServerError = pyqtSignal()
    parameterRemoved = pyqtSignal()
    parametersRefreshed = pyqtSignal()

    def __init__(self, reactor, parent=None):
        super(StatusClient, self).__init__(parent)
        self.reactor = reactor
        self.setGeometry(0, 0, 3*self.RAD, 3*self.RAD)
        self.alive = True
        self.state = -1
        self.error_flag = 0
 
        # define IDs for LABRAD signals
        self.ID_start = 11111
        self.ID_stop = 11112
        self.ID_par_removed = 11113
        self.ID_pars_refreshed = 11114
        
        # layout the GUI
        self.setupLayout()

        # start connections with LABRAD
        self.initialize()
    
    def initialize(self):
        self.connected = False
        self.reconnect = LoopingCall(self.connect)
        self.reconnect.start(3.0)


    @inlineCallbacks
    def connect(self): 
        try:
            if not self.connected:
                self.textedit.setTextColor(QColor(client_config.widget['colorWarning']))
                self.textedit.append("Trying to connect to LabRAD...")
                self.cxn = connection()
                yield self.cxn.connect()
                server = yield self.cxn.get_server('conductor')
                
                # Connect to experiment_started signal from conductor
                yield server.signal__experiment_started(self.ID_start)
                yield server.addListener(listener = self.started, source = None, ID = self.ID_start)
        
                # Connect to experiment_stopped signal from Conductor
                yield server.signal__experiment_stopped(self.ID_stop)
                yield server.addListener(listener = self.stopped, source = None, ID = self.ID_stop)
        
                # Connect to parameter_removed signal from Conductor
                yield server.signal__parameter_removed(self.ID_par_removed)
                yield server.addListener(listener = self.parameter_removed, source = None, ID = self.ID_par_removed)
        
                yield server.signal__parameters_refreshed(self.ID_pars_refreshed)
                yield server.addListener(listener=self.parameters_refreshed, source=None, ID = self.ID_pars_refreshed)

                yield self.cxn.add_on_disconnect('conductor', self.server_stopped)

                self.connected = True
                self.textedit.setTextColor(QColor(client_config.widget['colorOff']))
                self.textedit.append("Connected to LabRAD!")

                self.color = QColor(client_config.widget['colorOff'])
                self.update()
        except Exception as e:
            self.connected = False
            self.server_stopped("conductor not running")
        returnValue(self.connected)

    # Sets variables, writes a timestamp to the widget
    # Emits signal for the indicator to change color
    def started(self, cntx, signal):
        if not self.error_flag:
            self.alive = True
            timestr = time.strftime("%H:%M:%S", time.localtime())
            self.textedit.setTextColor(QColor(client_config.widget['colorOn']))
            self.textedit.append("started " + timestr)
            self.exptStarted.emit()
            self.callback = self.reactor.callLater(WAIT_TIME, self.abort_button.button.setEnabled, True)
            self.refresh_button.button.setEnabled(False)
        else:
            self.refresh_button.button.setEnabled(True)

    # Runs when the client gets the experiment_stopped signal from Conductor.
    # Prints timestamp to the widget and emits signal for the indicator to change color.
    def stopped(self, cntx, signal):
        if signal and self.alive:
            self.alive = False
            timestr = time.strftime("%H:%M:%S", time.localtime())
            self.textedit.setTextColor(QColor(client_config.widget['colorOff']))
            self.textedit.append("stopped " + timestr)
            self.exptStopped.emit()
            try:
                self.callback.cancel()
            except: pass
            self.abort_button.button.setEnabled(False)
            self.refresh_button.button.setEnabled(True)
        else:
            self.alive = False

    # Appends a message to the text edit and changes the color of the indicator widget
    # when a parameter is removed by conductor
    def parameter_removed(self, cntx, signal):
        self.error_flag = 1
        self.alive = False
        timestr = time.strftime("%H:%M:%S", time.localtime())
        self.textedit.setTextColor(QColor(client_config.widget['colorWarning']))
        self.textedit.append(signal + " removed " + timestr)
         
        self.error_message = QErrorMessage()
        self.error_message.showMessage(signal + " has been removed. You can still run the experiment if you don't need it.\n Otherwise, try to refresh parameters.")
        
        self.parameterRemoved.emit()
        self.refresh_button.button.setEnabled(True)


    def parameters_refreshed(self, cntx, signal):
        self.error_flag = 0
        self.parametersRefreshed.emit()

    # Appends a message to the text edit and changes the color of the indicator widget
    # when a server is stopped
    def server_stopped(self, message=""):
        self.error_flag = 1
        self.alive = False
        timestr = time.strftime("%H:%M:%S", time.localtime())
        self.textedit.setTextColor(QColor(client_config.widget['colorError']))
        if message:
            self.textedit.append(message + " " + timestr)
        else:
            self.textedit.append("conductor stopped " + timestr)
            self.connected = False
        self.labradServerError.emit()

    # Lays out the widget
    def setupLayout(self):
        self.setWindowTitle('Status Widget')
        #create a vertical layout
        layout = QVBoxLayout()
        # add the indicator to the widget and connect signals
        self.indicator = Indicator()
        self.exptStarted.connect(self.indicator.exptStarted)
        self.exptStopped.connect(self.indicator.exptStopped)
        self.labradServerError.connect(self.indicator.labradServerError)
        self.parameterRemoved.connect(self.indicator.parameterRemoved)
        self.parametersRefreshed.connect(self.indicator.parametersRefreshed)
        # add the abort button
        self.abort_button = AbortButton(self.reactor)
        self.abort_button.button.setEnabled(False)
        # add the refresh button
        self.refresh_button = RefreshButton(self.reactor)
        self.refresh_button.button.setEnabled(False)
        # create the text widget 
        self.textedit = QTextEdit()
        self.textedit.setReadOnly(True)
        # add widgets to layout
        layout.addWidget(self.indicator)
        layout.setStretch(0, 2)
        layout.addWidget(self.abort_button, alignment=Qt.AlignHCenter)
        layout.addWidget(self.refresh_button, alignment=Qt.AlignHCenter)
        layout.addWidget(self.textedit)
        self.setLayout(layout)

    # Writes state signal to widget
    def displaySignal(self, cntx, signal):
        self.textedit.append(signal)

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
    widget = StatusClient(reactor)
    widget.show()
    reactor.run()
