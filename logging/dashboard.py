import json
import sys
from PyQt5 import QtGui, QtCore, QtWidgets
import vlc
import pycurl
from io import BytesIO
from functools import partial

class lattice_block_gui(QtWidgets.QMainWindow):
    def __init__(self, Parent=None):
        super(lattice_block_gui, self).__init__(Parent)
        self.setWindowIcon(QtGui.QIcon("laser_icon.png"))
        self.setWindowTitle("KRb Laser Dashboard")
        self.initialize()
        self.url = 'http://192.168.141.220:8000/wavemeter/api/'

    def initialize(self):
        with open("logging_config.json", 'r') as f:
            config = json.load(f)

        main = QtWidgets.QGridLayout()
        sizepolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.buttons = []
        self.labels = []
        self.broken = []
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
            i += 1
        
        mainWidget = QtWidgets.QWidget()
        mainWidget.setLayout(main)
        self.setCentralWidget(mainWidget)

    def update(self):
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
            for (i, l) in enumerate(self.lasers):
                wl = 299792.458/self.data["wavelengths"][l['i']]
                label = "%.5f THz" % (wl)
                self.labels[i].setText(label)

                if (wl < l['min_freq'] or wl > l['max_freq']) and not self.broken[i]:
                    self.broken[i] = True
                    play = True
                    self.buttons[i].setStyleSheet('background-color: red')
            if play:
                sound = vlc.MediaPlayer('unlocked.mp3')
                sound.play()


        except pycurl.error as e:
            print("could not connect to wavemeter: ", e)
            self.data = ''

    def pressed(self, button, i):
        self.broken[i] = False
        self.buttons[i].setStyleSheet('background-color: light gray')


    def status(self):
        pass

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)

    # Set up window
    w = lattice_block_gui()
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
    sys.exit(ret)