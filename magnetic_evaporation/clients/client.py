from __future__ import print_function
from PyQt4 import QtCore, QtGui
import json
#from scratch import evaporation

import time

from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as Canvas
from matplotlib.figure import Figure

from matplotlib import rcParams
rcParams['font.size'] = 9

dT = 0.05

class MatplotlibWidget(Canvas):
    """
    MatplotlibWidget inherits PyQt4.QtGui.QWidget
    and matplotlib.backend_bases.FigureCanvasBase
    
    Options: option_name (default_value)
    -------    
    parent (None): parent widget
    title (''): figure title
    xlabel (''): X-axis label
    ylabel (''): Y-axis label
    xlim (None): X-axis limits ([min, max])
    ylim (None): Y-axis limits ([min, max])
    xscale ('linear'): X-axis scale
    yscale ('linear'): Y-axis scale
    width (4): width in inches
    height (3): height in inches
    dpi (100): resolution in dpi
    hold (False): if False, figure will be cleared each time plot is called
    
    Widget attributes:
    -----------------
    figure: instance of matplotlib.figure.Figure
    axes: figure axes
    
    Example:
    -------
    self.widget = MatplotlibWidget(self, yscale='log', hold=True)
    from numpy import linspace
    x = linspace(-10, 10)
    self.widget.axes.plot(x, x**2)
    self.wdiget.axes.plot(x, x**3)
    """
    def __init__(self, parent=None, title='', xlabel='', ylabel='',
                 xlim=None, ylim=None, xscale='linear', yscale='linear',
                 width=4, height=3, dpi=100, hold=False):
        self.figure = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.figure.add_subplot(111)
        self.axes.set_title(title)
        self.axes.set_xlabel(xlabel)
        self.axes.set_ylabel(ylabel)
        if xscale is not None:
            self.axes.set_xscale(xscale)
        if yscale is not None:
            self.axes.set_yscale(yscale)
        if xlim is not None:
            self.axes.set_xlim(*xlim)
        if ylim is not None:
            self.axes.set_ylim(*ylim)
        self.axes.hold(hold)

        Canvas.__init__(self, self.figure)
        self.setParent(parent)

        Canvas.setSizePolicy(self, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        Canvas.updateGeometry(self)

    def sizeHint(self):
        w, h = self.get_width_height()
        return QSize(w, h)

    def minimumSizeHint(self):
        return QSize(10, 10)


try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s

try:
    _encoding = QtGui.QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig)

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName(_fromUtf8("Trajectory Maker"))
        MainWindow.resize(903, 408)
        self.centralwidget = QtGui.QWidget(MainWindow)
        self.centralwidget.setObjectName(_fromUtf8("centralwidget"))

        self.A = loadtraj('../evap.json')
        self.headers = ['start','stop','tau','amplitudes','asymp']

        self.saveButton = QtGui.QPushButton(self.centralwidget)
        self.saveButton.setGeometry(QtCore.QRect(750, 310, 111, 51))
        self.saveButton.setObjectName(_fromUtf8("saveButton"))
        self.saveButton.clicked.connect(self.savefile)

        self.deleteButton = QtGui.QPushButton(self.centralwidget)
        self.deleteButton.setGeometry(QtCore.QRect(20, 310, 111, 51))
        self.deleteButton.setObjectName(_fromUtf8("deleteButton"))
        self.deleteButton.clicked.connect(self.delrow)

        self.addButton = QtGui.QPushButton(self.centralwidget)
        self.addButton.setGeometry(QtCore.QRect(150, 310, 111, 51))
        self.addButton.setObjectName(_fromUtf8("addButton"))
        self.addButton.clicked.connect(self.addrow)

        
        

        self.table = QtGui.QTableWidget(self.centralwidget)
        self.table.setGeometry(QtCore.QRect(20, 20, 541, 281))
        self.table.setRowCount(len(self.A[self.headers[0]]))
        self.table.setColumnCount(5)
        self.table.setObjectName(_fromUtf8("table"))
        self.table.setHorizontalHeaderLabels(self.headers)

        self.populatetable(self.A) #load evap.json and populate table

        self.table.cellChanged.connect(self.tabupdate)

        self.graph = MatplotlibWidget(self.centralwidget)
        self.graph.setGeometry(QtCore.QRect(580, 20, 311, 281))
        self.graph.setAutoFillBackground(False)
        self.graph.setObjectName(_fromUtf8("graph"))

        self.updategraph()


        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtGui.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 903, 21))
        self.menubar.setObjectName(_fromUtf8("menubar"))
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtGui.QStatusBar(MainWindow)
        self.statusbar.setObjectName(_fromUtf8("statusbar"))
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(_translate("MainWindow", "Trajectory Maker", None))
        self.saveButton.setText(_translate("MainWindow", "Save", None))
        self.deleteButton.setText(_translate("MainWindow", "Delete row", None))
        self.addButton.setText(_translate("MainWindow", "Add row", None))

    def populatetable(self, evap):
        for k in range(len(self.headers)):
            for j in range(len(evap[self.headers[k]])):
                self.table.setItem(j,k,QtGui.QTableWidgetItem(str(evap[self.headers[k]][j])))

    def tabupdate(self, row, column):
        nrowcomplete = len(self.A[self.headers[0]])
        #print(nrowcomplete)
        x = self.table.item(row,column).text()

        if not isnumber(x):
            self.showdialog()
            self.table.setItem(row,column,QtGui.QTableWidgetItem(str(0)))
        elif row+1 > nrowcomplete and self.rowcomplete(row):
            for k in range(5):
                self.A[self.headers[k]].append(float(self.table.item(row,k).text()))
            self.updategraph()
            print(self.A)
        elif self.getrows() == nrowcomplete and row < nrowcomplete:
            self.A[self.headers[column]][row] = float(self.table.item(row,column).text())
            print(self.A)
            self.updategraph()


    def getrows(self):
        n = 0
        while True:
            try:
                x = self.table.item(n,0).text()
                if self.rowcomplete(n):
                    n += 1
                else:
                    break
            except AttributeError:
                break
        return n

    def rowcomplete(self,n):
        for k in range(5):
            try:
                x = self.table.item(n,k).text()
            except AttributeError:
                return False
        return True

    def showdialog(self):
        d = QtGui.QDialog()
        d.resize(180,100)

        b1 = QtGui.QPushButton("ok",d)
        b1.move(50,50)
        b1.clicked.connect(d.accept)

        l1 = QtGui.QLabel("Parameters should all be numbers!",d)
        l1.move(10,20)

        d.setWindowTitle("Error")
        d.setWindowModality(QtCore.Qt.ApplicationModal)
        d.exec_()

    def savefile(self):
        #Stamp the current trajectory with time
        import time, datetime
        self.A['timestamp'] = datetime.datetime.fromtimestamp(time.time()).strftime('%Y%m%d%H%M%S') 

        #Backup the old trajectory
        x = loadtraj('../evap.json')
        backpath = '../backup/evap'+str(x['timestamp'])+'.json'
        with open(backpath, 'w') as outfile:
            json.dump(x,outfile)

        #save new trajectory
        with open('../evap.json', 'w') as outfile:
            json.dump(self.A,outfile)

    def updategraph(self):
        import numpy as np
        F = np.array([])
        for k in range(self.getrows()):
            x = exponential(self.A['start'][k],self.A['stop'][k],self.A['asymp'][k],self.A['tau'][k])
            F = np.append(F,x)
        T = np.arange(len(F))*dT
	MaxTime = T[-1]
	print(MaxTime)
	
        self.graph.axes.clear()
        self.graph.axes.plot(T,F)
	print(F[-1])
        fick = "Evap. Time: {0:.2f} s".format(MaxTime)
	self.graph.axes.set_title(fick)
        self.graph.draw()

    def delrow(self):
        self.table.removeRow(self.table.rowCount()-1)
	for k in range(5):
		self.A[self.headers[k]] = self.A[self.headers[k]][0:-1]
	self.updategraph()
        return True

    def addrow(self):
        self.table.insertRow(self.table.rowCount())
        return True
     

#from matplotlibwidget import MatplotlibWidget

def loadtraj(path):
    with open(path, 'r') as infile:
        evap = json.load(infile)

    A = {}
    for key, values in evap.items():
        A[key] = values
    return A

def isnumber(s):
    try:
        float(s)
        return True
    except ValueError:
        return False

    
def exponential(fi,fs,fa,tau):
    import numpy as np
    if fi <= fa or fs <= fa:
        raise Exception("Initial and final frequencies must be larger than asymptotic frequency")
    
    if fi > fs:
        tf = tau*np.log((float(fi)-fa)/(fs-fa))
        N = int(np.floor(tf/dT))

        
        Y = np.zeros(N)
        T = np.zeros(N)
        for k in range(int(N)):
            T[k] = k*dT
            Y[k] = (fi-fa)*np.exp(-T[k]/tau) + fa
        return Y

if __name__ == "__main__":
    import sys
    app = QtGui.QApplication(sys.argv)
    MainWindow = QtGui.QMainWindow()
    ui = Ui_MainWindow()
    ui.setupUi(MainWindow)
    MainWindow.setWindowIcon(QtGui.QIcon('./icon.png'))
    MainWindow.show()
    sys.exit(app.exec_())

