import json
import time
import numpy as np
import os
import sys

from PyQt4 import QtGui, QtCore, Qt
from PyQt4.QtCore import pyqtSignal 
from twisted.internet.defer import inlineCallbacks

# sys.path.append('./displays/')
# from display_gui_elements import *

SEP = os.path.sep

class SequenceTable(QtGui.QTableWidget):
    def __init__(self):
        super(SequenceTable, self).__init__()
        self.setColumnCount(2)
        self.setRowCount(1)

        self.setHorizontalHeaderLabels(["Module", "Date"])
        self.ncols = 2

    def update(self, sequence):
        for i in range(self.rowCount()):
            self.removeRow(0)

        for i, s in enumerate(sequence):
            self.insertRow(i)

            m = QtGui.QTableWidgetItem(s[0])
            m.setFlags(QtCore.Qt.ItemIsSelectable)
            d = QtGui.QTableWidgetItem(s[1])
            d.setFlags(QtCore.Qt.ItemIsSelectable)

            self.setItem(i, 0, m)
            self.setItem(i, 1, d)




