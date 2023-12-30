import json
import sys
from PyQt5 import QtGui, QtCore, QtWidgets
from PyQt5.QtWidgets import QMenu, QAction
import pycurl
from io import BytesIO
from functools import partial
import random
from time import time
import labrad

# TODO: Fix Sphinx autodoc reporting the superclass as sphinx.ext.autodoc.importer._MockObject
class laser_dashboard_gui(QtWidgets.QMainWindow):
    """
    Displays the status of the laser locks, including the measured laser frequencies and an indicator if the laser is unlocked. Also provides audible warnings when lasers come unlocked.
    """
    def __init__(self, Parent=None):
        super(laser_dashboard_gui, self).__init__(Parent)
        self.setWindowIcon(QtGui.QIcon("laser_icon.png"))
        self.setWindowTitle("KRb Laser Dashboard")
        self.initialize()
        self.cxn = labrad.connect()
        self.alerter = self.cxn.polarkrb_alerter
        self.wavemeter = self.cxn.wavemeterlaptop_wavemeter
        self._createMenuBar()

    def _createMenuBar(self):
        menuBar = self.menuBar()
        eFieldMenu = menuBar.addMenu("&Field")
   
        actions = []
        filenames = range(0,len(self.stirap))
        for filename in filenames:
            action = QAction(str(self.stirap[filename]['i']), self)
            action.triggered.connect(lambda checked, index=filename: self.updateStirapField(index))
            actions.append(action)

        # Step 3. Add the actions to the menu
        eFieldMenu.addActions(actions)

    def updateStirapField(self, i):
        ## update label
        self.buttons[0].setText("UpLeg " + str(self.stirap[i]['i'])+" kV/cm")
        self.buttons[4].setText("DownLeg " + str(self.stirap[i]['i'])+" kV/cm")
        
        ## update max/min 
        xDet = 0.0001  ## frequency range

        self.lasers[0].update({"label": "UpLeg " + str(self.stirap[i]['i'])+" kV/cm", "max_freq": self.stirap[i]["fUpLeg"]+xDet, "min_freq": self.stirap[i]["fUpLeg"]-xDet})
        self.lasers[4].update({"label": "DownLeg " + str(self.stirap[i]['i'])+" kV/cm", "max_freq": self.stirap[i]["fDownLeg"]+xDet, "min_freq": self.stirap[i]["fDownLeg"]-xDet})
        self.update()
        # print(self.stirap[i]["fUpLeg"])

        


    def initialize(self):
        """
       lays out buttons and labels in the window per the channels listed in the config file.
        """
        # with open("logging_config.json", 'r') as f:
            # config = json.load(f)

        config={"wavemeter": 
            {
                "channels":
                [
                    { "i": 0, "label": "Up Leg", "max_freq": 309.6028, "min_freq": 309.6026},
                    { "i": 4, "label": "Unused", "max_freq": 1E3, "min_freq": 1},
                    { "i": 2, "label": "D1", "max_freq": 389.2870, "min_freq": 389.286915},
                    { "i": 3, "label": "K Repump", "max_freq":391.01626, "min_freq": 391.01616},
                    { "i": 1, "label": "Down Leg", "max_freq": 434.9232, "min_freq": 434.9228},
                    { "i": 5, "label": "Rb Trap", "max_freq": 384.2295, "min_freq": 384.2279},
                    { "i": 6, "label": "Rb Repump", "max_freq": 384.23482, "min_freq": 384.23472},
                    { "i": 9, "label": "K Trap", "max_freq": 1370, "min_freq": 400}
                ]
            }
        }
        stirapFields={"fields":[
                    { "i": 0,      "fUpLeg":309.60298,  "fDownLeg":434.92253},
                    { "i": 1,      "fUpLeg":309.60307,  "fDownLeg":434.92264},
                    { "i": 1.5,    "fUpLeg":309.60305,  "fDownLeg":434.92284},
                    { "i": 2.7,    "fUpLeg":309.60306,  "fDownLeg":434.92293},
                    { "i": 3.5,    "fUpLeg":309.60303,  "fDownLeg":434.92296},
                    { "i": 4.6,    "fUpLeg":309.60297,  "fDownLeg":434.92289},
                    { "i": 5.5,    "fUpLeg":309.60275,  "fDownLeg":434.92298},
                    { "i": 6.5,    "fUpLeg":309.60280,  "fDownLeg":434.92300},
                    { "i": 9.0,    "fUpLeg":309.60246,  "fDownLeg":434.92296},
                    { "i": 12.7,   "fUpLeg":309.60163,  "fDownLeg":434.92287}
                ]
        }



        main = QtWidgets.QGridLayout()
        sizepolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.buttons = []
        self.labels = []
        self.broken = []
        self.t_good = []
        i = 0
        self.lasers = config['wavemeter']['channels']
        self.stirap = stirapFields["fields"]
        for laser in self.lasers:
            if True:
                button = QtWidgets.QPushButton()
                button.setText(laser['label'])
                button.setSizePolicy(sizepolicy)
                button.setFont(QtGui.QFont('Comic Sans', 24))
                button.pressed.connect(partial(self.pressed, button, i))

                label = QtWidgets.QLabel()
                label.setText('0.00000 THz')
                label.setSizePolicy(sizepolicy)
                label.setFont(QtGui.QFont('Comic Sans', 24))
                label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
                main.addWidget(button, i, 0)
                main.addWidget(label, i, 1)
                self.buttons.append(button)
                self.labels.append(label)
                self.broken.append(False)
                self.t_good.append(time())
        
            i += 1
            
        mainWidget = QtWidgets.QWidget()
        mainWidget.setLayout(main)
        self.setCentralWidget(mainWidget)

    def update(self):
        """
        Gets the latest data from the wavemeter and updates buttons and plays warning audio if laser is unlocked.
        """
        # c = pycurl.Curl()
        try:
            try:
                self.data = json.loads(json.loads(self.wavemeter.get_wavelengths()))
            except Exception as e:
                print("could not connect to wavemeter: ", e)
            play = False
            names = []

            for (i, l) in enumerate(self.lasers):
                if l['i'] < 8:
                    wl = 299792.458/self.data["wavelengths"][l['i']]
                    label = "%.6f THz" % (wl)
                else:
                    wl = self.data["freq"]
                    label = "%.2f MHz" % (wl)
                self.labels[i].setText(label)

                if (wl >= l['min_freq'] and wl <= l['max_freq']):
                    if self.t_good[i] == 0:
                        self.t_good[i] = time()
                else:
                    self.t_good[i] = 0

                if (wl < l['min_freq'] or wl > l['max_freq']) and ((100 < wl and 800 > wl) or l['i'] >= 8) and not self.broken[i]:
                    print(l, wl)
                    self.broken[i] = True
                    play = True
                    self.buttons[i].setStyleSheet('background-color: red')
                    self.buttons[i].repaint()
                    names.append(l['label'])

                if self.broken[i] and time() - self.t_good[i] > 10 and self.t_good[i] != 0:
                    self.pressed(self.buttons[i], i)
            if play:
                for n in names:
                    r = random.random()
                    if r > 0.99:
                        s = "Papa Jun is always watching"
                    elif r < 0.1:
                        s = "Thank you papa Cal for giving me life, for birthing me"
                    elif r > 0.7:
                        s = ""
                    else:
                        s = ""
                    self.alerter.say(("The %s laser is unlocked!" + s) % (n))
        except pycurl.error as e:
            print("could not connect to wavemeter: ", e)
            self.data = ''

    def pressed(self, button, i):
        """
        Resets unlocked status when a button corresponding to a laser is pressed.

        Args:
            button (QtWidgets.QPushButton): The button that was pressed
            i (int): The index of the button
        """
        self.broken[i] = False
        self.buttons[i].setStyleSheet('background-color: light gray')


    def status(self):
        """
        Called every 100 ms.
        """
        pass

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)

    # Set up window
    w = laser_dashboard_gui()
    # w.setGeometry(100, 100, 1200, 380)
    w.show()

    # Call Python every 100 ms so Ctrl-c works
    timer = QtCore.QTimer()
    timer.timeout.connect(w.status)
    timer.start(100)

    timer2 = QtCore.QTimer()
    timer2.timeout.connect(w.update)
    timer2.start(500)

    # Run event loop
    ret = app.exec_()
    app.engine.stop()
    sys.exit(ret)