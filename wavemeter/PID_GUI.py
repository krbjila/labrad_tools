from PyQt5 import QtCore, QtGui, QtWidgets
from pyqtgraph import PlotWidget, plot
import pyqtgraph as pg
from json import loads
from collections import deque
from time import time

from simple_pid import PID
import labrad
from twisted.internet.defer import inlineCallbacks

import board
import busio
import adafruit_mcp4728

# Class implementing a PID controller GUI, including a plot of the PID output and textboxes for the gains and setpoint
class PID_GUI(QtWidgets.QWidget):

    default_piezo_kP = 0
    default_piezo_kI = 0.01
    default_piezo_kD = 0

    default_current_kP = 0
    default_current_kI = 0.01
    default_current_kD = 0

    default_setpoint = round(299792.458 / 1028.7397, 6) # THz
    default_piezo = 2.048 # V
    default_current = 2.048 # V

    default_dt = 0.05 # seconds
    default_plot_span = 30 # seconds
    default_channel = 2

    ID = 314159265

    def __init__(self, parent=None):
        super(PID_GUI, self).__init__(parent)

        # Initialize the GUI
        self.initUI()

        # Initialize the PID controllers for the piezo and current
        self.piezo_output = PID_GUI.default_piezo
        self.current_output = PID_GUI.default_current
        self.set_piezo(self.piezo_output)
        self.piezo_output_display.setText(str(self.piezo_output))
        self.set_current(self.current_output)
        self.current_output_display.setText(str(self.current_output))

        self.setpoint = PID_GUI.default_setpoint
        self.piezo_pid = PID(PID_GUI.default_piezo_kP, PID_GUI.default_piezo_kI, PID_GUI.default_piezo_kD, setpoint=self.setpoint)
        self.piezo_pid.output_limits = (0, 4.096)
        self.piezo_pid.auto_mode = False
        self.piezo_pid.proportional_on_measurement = True

        self.current_pid = PID(PID_GUI.default_current_kP, PID_GUI.default_current_kI, PID_GUI.default_current_kD, setpoint=self.setpoint)
        self.current_pid.output_limits = (0, 4.096)
        self.current_pid.auto_mode = False
        self.current_pid.proportional_on_measurement = True

        # Initialize the data arrays for the plots
        self.plot_array_length = int(PID_GUI.default_plot_span / PID_GUI.default_dt)
        self.time_data = deque(maxlen=self.plot_array_length)
        self.error_data = deque(maxlen=self.plot_array_length)
        self.piezo_output_data = deque(maxlen=self.plot_array_length)
        self.current_output_data = deque(maxlen=self.plot_array_length)

        # Initialize the curves on the plots
        self.error_curve = self.error_plot.plot()
        self.output_plot.addLegend()
        self.piezo_output_curve = self.output_plot.plot(name="Piezo Output")
        self.current_output_curve = self.output_plot.plot(name="Current Output")

        # Set the colors of the output curves
        self.piezo_output_curve.setPen(pg.mkPen(color=(255, 0, 0), width=2))
        self.current_output_curve.setPen(pg.mkPen(color=(0, 0, 255), width=2))

        # Initialize the DAC board
        self.i2c = busio.I2C(board.SCL, board.SDA)
        self.dac = adafruit_mcp4728.MCP4728(self.i2c)
        self.dac.channel_a.vref = adafruit_mcp4728.Vref.INTERNAL
        self.dac.channel_a.gain = 2
        self.dac.channel_b.vref = adafruit_mcp4728.Vref.INTERNAL
        self.dac.channel_b.gain = 2

        # Connect the buttons to their functions
        self.start.clicked.connect(self.start_PID)
        self.stop.clicked.connect(self.stop_PID)
        self.clear.clicked.connect(self.clear_plots)

        # Connect to labrad
        self.connect()

        # Add a listener for labrad's setpoint signal
        # self.wavemeter.signal__setpoint_changed.connect(self.setpoint_changed)
        # self.wavemeter.addListener(listener=self.setpoint_changed, source=None, ID=PID_GUI.ID)

        # Record the start time
        self.start_time = time()

        # Start the PID loop
        self.timer = QtCore.QTimer()
        self.timer.setInterval(PID_GUI.default_dt * 1000)
        self.timer.timeout.connect(self.run_PID)
        self.timer.start()

    def connect(self):
        self.cxn = labrad.connect()
        self.wavemeter = self.cxn.wavemeterlaptop_wavemeter

    def initUI(self):
            
        # Create the layout
        layout = QtWidgets.QGridLayout()
        controls_layout = QtWidgets.QGridLayout()

        layout.addLayout(controls_layout, 2, 0)

        # Create plots for the error and PID output
        self.error_plot = pg.PlotWidget()
        self.error_plot.setMinimumSize(400, 150)
        self.error_plot.setLabel('left', 'Error', units='Hz')
        self.error_plot.setLabel('bottom', 'Time', units='s')
        layout.addWidget(self.error_plot, 0, 0)

        self.output_plot = pg.PlotWidget()
        self.output_plot.setMinimumSize(400, 150)
        self.output_plot.setLabel('left', 'PID Output', units='V')
        self.output_plot.setLabel('bottom', 'Time', units='s')
        layout.addWidget(self.output_plot, 1, 0)
        
        # Create labeled textboxes for the gains for the piezo PID that don't resize with the window
        self.piezo_label = QtWidgets.QLabel("Piezo PID")
        controls_layout.addWidget(self.piezo_label, 1, 1)

        self.Kp_piezo = QtWidgets.QLineEdit(str(PID_GUI.default_piezo_kP))
        self.Kp_piezo.setValidator(QtGui.QDoubleValidator())
        self.Kp_piezo.editingFinished.connect(self.update_gains)
        self.Kp_piezo_label = QtWidgets.QLabel("P")
        self.Kp_piezo_label.setAlignment(QtCore.Qt.AlignRight)
        controls_layout.addWidget(self.Kp_piezo_label, 2, 0)
        controls_layout.addWidget(self.Kp_piezo, 2, 1)

        self.Ki_piezo = QtWidgets.QLineEdit(str(PID_GUI.default_piezo_kI))
        self.Ki_piezo.setValidator(QtGui.QDoubleValidator())
        self.Ki_piezo.editingFinished.connect(self.update_gains)
        self.Ki_piezo_label = QtWidgets.QLabel("I")
        self.Ki_piezo_label.setAlignment(QtCore.Qt.AlignRight)
        controls_layout.addWidget(self.Ki_piezo_label, 3, 0)
        controls_layout.addWidget(self.Ki_piezo, 3, 1)

        self.Kd_piezo = QtWidgets.QLineEdit(str(PID_GUI.default_piezo_kD))
        self.Kd_piezo.setValidator(QtGui.QDoubleValidator())
        self.Kd_piezo.editingFinished.connect(self.update_gains)
        self.Kd_piezo_label = QtWidgets.QLabel("D")
        self.Kd_piezo_label.setAlignment(QtCore.Qt.AlignRight)
        controls_layout.addWidget(self.Kd_piezo_label, 4, 0)
        controls_layout.addWidget(self.Kd_piezo, 4, 1)

        # Create labeled textboxes for the gains for the current PID
        self.current_label = QtWidgets.QLabel("Current PID")
        controls_layout.addWidget(self.current_label, 1, 4)

        self.Kp_current = QtWidgets.QLineEdit(str(PID_GUI.default_current_kP))
        self.Kp_current.setValidator(QtGui.QDoubleValidator())
        self.Kp_current.editingFinished.connect(self.update_gains)
        self.Kp_current_label = QtWidgets.QLabel("P")
        self.Kp_current_label.setAlignment(QtCore.Qt.AlignRight)
        controls_layout.addWidget(self.Kp_current_label, 2, 3)
        controls_layout.addWidget(self.Kp_current, 2, 4)

        self.Ki_current = QtWidgets.QLineEdit(str(PID_GUI.default_current_kI))
        self.Ki_current.setValidator(QtGui.QDoubleValidator())
        self.Ki_current.editingFinished.connect(self.update_gains)
        self.Ki_current_label = QtWidgets.QLabel("I")
        self.Ki_current_label.setAlignment(QtCore.Qt.AlignRight)
        controls_layout.addWidget(self.Ki_current_label, 3, 3)
        controls_layout.addWidget(self.Ki_current, 3, 4)

        self.Kd_current = QtWidgets.QLineEdit(str(PID_GUI.default_current_kD))
        self.Kd_current.setValidator(QtGui.QDoubleValidator())
        self.Kd_current.editingFinished.connect(self.update_gains)
        self.Kd_current_label = QtWidgets.QLabel("D")
        self.Kd_current_label.setAlignment(QtCore.Qt.AlignRight)
        controls_layout.addWidget(self.Kd_current_label, 4, 3)
        controls_layout.addWidget(self.Kd_current, 4, 4)

        # Add a horizontal line to separate the piezo and current PID controls
        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.HLine)
        line.setFrameShadow(QtWidgets.QFrame.Sunken)
        controls_layout.addWidget(line, 5, 0, 1, 5)

        # Create a textbox for the setpoint
        self.setpoint_display = QtWidgets.QLineEdit(str(PID_GUI.default_setpoint))
        self.setpoint_display.setValidator(QtGui.QDoubleValidator())
        self.setpoint_display.editingFinished.connect(self.update_setpoint)
        self.setpoint_label = QtWidgets.QLabel("Setpoint")
        controls_layout.addWidget(self.setpoint_label, 6, 0)
        controls_layout.addWidget(self.setpoint_display, 6, 1)

        # Add a dropdown menu to select the wavemeter channel from 1-8
        self.channel = QtWidgets.QComboBox()
        self.channel.addItems(["1", "2", "3", "4", "5", "6", "7", "8"])
        self.channel.setCurrentIndex(PID_GUI.default_channel - 1)
        controls_layout.addWidget(self.channel, 6, 3)
        self.channel_label = QtWidgets.QLabel("Channel")
        controls_layout.addWidget(self.channel_label, 6, 2)

        # Create the button to start the PID
        self.start = QtWidgets.QPushButton("Start")
        controls_layout.addWidget(self.start, 7, 1)

        # Create the button to stop the PID
        self.stop = QtWidgets.QPushButton("Stop")
        self.stop.setDisabled(True)
        controls_layout.addWidget(self.stop, 7, 3)

        # Create the button to clear the plots
        self.clear = QtWidgets.QPushButton("Clear")
        controls_layout.addWidget(self.clear, 7, 4)

        # Add a horizontal line to separate the controls from the status
        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.HLine)
        line.setFrameShadow(QtWidgets.QFrame.Sunken)
        controls_layout.addWidget(line, 8, 0, 1, 5)

        # Display the current frequency and output values
        self.frequency_label = QtWidgets.QLabel("Frequency (THz)")
        self.frequency_label.setAlignment(QtCore.Qt.AlignRight)
        self.frequency_display = QtWidgets.QLabel()
        self.frequency_display.setDisabled(True)
        controls_layout.addWidget(self.frequency_label, 9, 0)
        controls_layout.addWidget(self.frequency_display, 9, 1)

        self.error_label = QtWidgets.QLabel("Error (THz)")
        self.error_label.setAlignment(QtCore.Qt.AlignRight)
        self.error_display = QtWidgets.QLabel()
        self.error_display.setDisabled(True)
        controls_layout.addWidget(self.error_label, 9, 2)
        controls_layout.addWidget(self.error_display, 9, 3)

        self.piezo_output_label = QtWidgets.QLabel("Piezo Output")
        self.piezo_output_label.setAlignment(QtCore.Qt.AlignRight)
        self.piezo_output_display = QtWidgets.QLineEdit("0")
        self.piezo_output_display.setDisabled(False)
        self.piezo_output_display.setValidator(QtGui.QDoubleValidator(0, 4.096, 5))
        self.piezo_output_display.editingFinished.connect(self.piezo_output_changed)
        controls_layout.addWidget(self.piezo_output_label, 10, 0)
        controls_layout.addWidget(self.piezo_output_display, 10, 1)

        self.current_output_label = QtWidgets.QLabel("Current Output")
        self.current_output_label.setAlignment(QtCore.Qt.AlignRight)
        self.current_output_display = QtWidgets.QLineEdit("0")
        self.current_output_display.setDisabled(False)
        self.current_output_display.setValidator(QtGui.QDoubleValidator(0, 4.096, 5))
        self.current_output_display.editingFinished.connect(self.current_output_changed)
        controls_layout.addWidget(self.current_output_label, 10, 2)
        controls_layout.addWidget(self.current_output_display, 10, 3)

        # Add a last column that stretches to fill the empty space
        controls_layout.setColumnStretch(5, 1)

        # Set the layout
        self.setLayout(layout)
        self.adjustSize()

        # Set the window title
        self.setWindowTitle("Wavemeter PID Lock")

        # Show the window
        self.show()

    def start_PID(self):
        # Start the PID
        self.piezo_pid.set_auto_mode(True, last_output=self.piezo_output)
        self.current_pid.set_auto_mode(True, last_output=self.current_output)
        self.piezo_output_display.setDisabled(True)
        self.current_output_display.setDisabled(True)
        self.start.setDisabled(True)
        self.stop.setDisabled(False)

    def stop_PID(self):
        # Stop the PID
        self.piezo_pid.set_auto_mode(False)
        self.current_pid.set_auto_mode(False)
        self.piezo_output_display.setDisabled(False)
        self.current_output_display.setDisabled(False)
        self.start.setDisabled(False)
        self.stop.setDisabled(True)

    def update_setpoint(self):
        # Update the setpoint
        self.setpoint = float(self.setpoint_display.text())

    def update_gains(self):
        # Update the gains
        self.piezo_pid.Kp = float(self.Kp_piezo.text())
        self.piezo_pid.Ki = float(self.Ki_piezo.text())
        self.piezo_pid.Kd = float(self.Kd_piezo.text())
        self.current_pid.Kp = float(self.Kp_current.text())
        self.current_pid.Ki = float(self.Ki_current.text())
        self.current_pid.Kd = float(self.Kd_current.text())

    def run_PID(self):
        # Run the PID
        frequency = self.get_frequency(self.channel.currentIndex())
        error = self.setpoint - frequency
        self.error_display.setText(str(round(error, 6)))
        if self.piezo_pid.auto_mode:
            self.piezo_output = self.piezo_pid(frequency)
            self.piezo_output_display.setText(str(round(self.piezo_output, 3)))
            self.set_piezo(self.piezo_output)
        if self.current_pid.auto_mode:
            self.current_output = self.current_pid(frequency)
            self.current_output_display.setText(str(round(self.current_output, 3)))
            self.set_current(self.current_output)
        
        # Set the outputs
        self.set_piezo(self.piezo_output)
        self.set_current(self.current_output)

        # Set the output display background to red when the output is saturated
        if self.piezo_output == 4.096 or self.piezo_output == 0:
            self.piezo_output_display.setStyleSheet("background-color: red")
        else:
            self.piezo_output_display.setStyleSheet("background-color: white")

        if self.current_output == 4.096 or self.current_output == 0:
            self.current_output_display.setStyleSheet("background-color: red")
        else:
            self.current_output_display.setStyleSheet("background-color: white")

        # Update the scrolling plot
        self.time_data.append(time() - self.start_time)
        self.error_data.append(error*1E12)
        self.piezo_output_data.append(self.piezo_output)
        self.current_output_data.append(self.current_output)
        self.error_curve.setData(self.time_data, self.error_data)
        self.piezo_output_curve.setData(self.time_data, self.piezo_output_data)
        self.current_output_curve.setData(self.time_data, self.current_output_data)

    def piezo_output_changed(self):
        # Update the piezo output
        self.piezo_output = float(self.piezo_output_display.text())
        self.set_piezo(self.piezo_output)

    def current_output_changed(self):
        # Update the current output
        self.current_output = float(self.current_output_display.text())
        self.set_current(self.current_output)

    def get_frequency(self, channel):
        # Get the frequency from the wavemeter
        data = loads(loads(self.wavemeter.get_wavelengths()))
        wavelength = data["wavelengths"][channel]
        frequency = 299792.458/wavelength
        self.frequency_display.setText(str(round(frequency, 6)))
        return frequency
    
    def clear_plots(self):
        # Clear the plot
        self.time_data = deque(maxlen=self.plot_array_length)
        self.error_data = deque(maxlen=self.plot_array_length)
        self.piezo_output_data = deque(maxlen=self.plot_array_length)
        self.current_output_data = deque(maxlen=self.plot_array_length)
    
    def set_piezo(self, output):
        self.dac.channel_a.value = int(self.piezo_output * 4095 / 4.096)

    def set_current(self, output):
        self.dac.channel_b.value = int(self.piezo_output * 4095 / 4.096)

if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    ex = PID_GUI()
    app.exec_()