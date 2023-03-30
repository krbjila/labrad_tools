import json
import sys
from PyQt5 import QtGui, QtCore, QtWidgets
import pycurl
from io import BytesIO
from functools import partial
import pyttsx3
import random
from time import time

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
        self.url = 'http://192.168.141.125:8000/wavemeter/api/'
        self.engine = pyttsx3.init()
        self.engine.startLoop(False)

    def initialize(self):
        """
        Loads the config file ``logging_config.json`` and lays out buttons and labels in the window per the channels listed in the config file.
        """
        with open("logging_config.json", 'r') as f:
            config = json.load(f)

        main = QtWidgets.QGridLayout()
        sizepolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.buttons = []
        self.labels = []
        self.broken = []
        self.t_good = []
        i = 0
        self.lasers = config['wavemeter']['channels']
        for laser in self.lasers:
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
        c = pycurl.Curl()
        try:
            buffer = BytesIO()
            c.setopt(c.URL, self.url)
            c.setopt(c.WRITEDATA, buffer)
            c.setopt(c.TIMEOUT_MS, 100)
            c.perform()
            c.close()
            body = buffer.getvalue()
            self.data = json.loads(body.decode('iso-8859-1'))
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
                # sound = vlc.MediaPlayer('unlocked.mp3')
                # sound.play()
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
                    self.engine.say(("The %s laser is unlocked!" + s) % (n))
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
        Called every 100 ms. Updates text-to-speech engine.
        """
        self.engine.iterate()

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