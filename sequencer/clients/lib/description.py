import sys
import json
from PyQt4 import QtGui, QtCore
from twisted.internet.defer import inlineCallbacks, returnValue
import numpy as np

sys.path.append('../../../client_tools')
from connection import connection
from widgets import SuperSpinBox

from copy import deepcopy

# Dialog for viewing and editing sequence annotations
class DescriptionDialog(QtGui.QDialog):
    def __init__(self, sequence, descriptions):
        super(DescriptionDialog, self).__init__()
        self.sequence = sequence
        self.descriptions = descriptions
        self.populate()
        self.connectSignals()

    def populate(self):
        self.setWindowTitle("Sequence column comments")

        # Get a random channel of the sequence
        # This is a list of dicts, each dict corresponding to a timestep
        val = self.sequence.values()[0]

        # If the number of descriptions is not correct,
        # just clear them all
        if len(self.descriptions) != len(val):
            self.descriptions = ['']*len(val)

        self.layout = QtGui.QVBoxLayout()

        self.table = DescriptionTable(val, self.descriptions)
        self.scroll = QtGui.QScrollArea()
        self.scroll.setWidget(self.table)

        self.buttons = QtGui.QDialogButtonBox(QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Cancel, QtCore.Qt.Horizontal, self)
        self.buttons.button(QtGui.QDialogButtonBox.Ok).setDefault(False)
        self.buttons.button(QtGui.QDialogButtonBox.Cancel).setDefault(True)

        self.layout.addWidget(self.scroll)
        self.layout.addWidget(self.buttons)
        self.setLayout(self.layout) 

    def connectSignals(self):
        self.buttons.accepted.connect(self.acceptAction)
        self.buttons.rejected.connect(self.reject)

    # Collect the descriptions before accepting
    def acceptAction(self):
        self.descriptions = []
        for e in self.table.edits:
            self.descriptions.append(str(e.toPlainText()))
        self.accept()

    def getDescriptions(self):
        return self.descriptions

# Table of column times and descriptions
class DescriptionTable(QtGui.QDialog):
    def __init__(self, sequence, descriptions):
        super(DescriptionTable, self).__init__()
        self.sequence = sequence
        self.descriptions = descriptions
        self.populate()

    def populate(self):
        self.layout = QtGui.QGridLayout()

        units = [(0, 's'), (-3, 'ms'), (-6, 'us'), (-9, 'ns')]
        self.times = []
        self.edits = []

        # Sequence is random channel's sequence;
        # all we need are the times
        for i in range(len(self.sequence)):
            b = SuperSpinBox([500e-9, 60], units)
            b.display(self.sequence[i]['dt'])
            b.setDisabled(True)
            b.setFixedWidth(90)

            e = QtGui.QPlainTextEdit(self.descriptions[i])
            e.setFixedWidth(90)
            e.setTabChangesFocus(True)

            self.times.append(b)
            self.edits.append(e)

            self.layout.addWidget(self.times[i], 0, i)
            self.layout.addWidget(self.edits[i], 1, i)
        self.setLayout(self.layout) 

