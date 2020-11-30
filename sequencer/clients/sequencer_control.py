from __future__ import print_function
from __future__ import absolute_import
import json
import time
import numpy as np
import os
import sys

from PyQt4 import QtGui, QtCore, Qt
from PyQt4.QtCore import pyqtSignal 
from twisted.internet.defer import inlineCallbacks

sys.path.append('../../client_tools')
from connection import connection
from widgets import SuperSpinBox
from .lib.duration_widgets import DurationRow
from .lib.digital_widgets import DigitalControl
from .lib.analog_widgets import AnalogControl

from .lib.ad5791_widgets import AD5791Control
from .lib.ad5791_editor import AD5791VoltageEditor

from .lib.electrode_widgets import ElectrodeControl
from .lib.electrode_editor import ElectrodeEditor, zero_sequence

from .lib.description import DescriptionDialog

from .lib.add_dlt_widgets import AddDltRow
from .lib.analog_editor import AnalogVoltageEditor
from .lib.analog_manual_control import AnalogVoltageManualControl
from .lib.analog_manual_control import ControlConfig as AnalogControlConfig
from .lib.helpers import get_sequence_parameters, ConfigWrapper

from copy import deepcopy

SEP = os.path.sep

# minimum sequence time for running the sequence from the client
# if this is small, then the code can hang due to 
# the latency in loading the sequences to the FPGAs
MIN_SEQ_TIME = 0.3

class LoadSaveRun(QtGui.QWidget):
    """ Tool bar for entering filenames, loading, saving and running """
    def __init__(self):
        super(LoadSaveRun, self).__init__(None)
        self.populate()

    def populate(self):
        self.locationBox = QtGui.QLineEdit()
        self.loadButton = QtGui.QPushButton('Load')
        self.saveButton = QtGui.QPushButton('Save')
        self.runButton = QtGui.QPushButton('Run')
        self.layout = QtGui.QHBoxLayout()
        self.layout.setContentsMargins(0, 5, 0, 5)
        self.layout.addWidget(self.locationBox)
        self.layout.addWidget(self.loadButton)
        self.layout.addWidget(self.saveButton)
        self.layout.addWidget(self.runButton)
        self.setLayout(self.layout)

class SequencerControl(QtGui.QWidget):
    def __init__(self, reactor, config_path='./config.json', cxn=None):
        super(SequencerControl, self).__init__(None)
        self.sequence_parameters = {}
        self.reactor = reactor
        self.load_config(config_path)
        self.cxn = cxn

        self.metadata = {}

        self.connect()

    def load_config(self, path=None):
        if path is not None:
            self.config_path = path
        with open(self.config_path, 'r') as infile:
            config = json.load(infile)
            self.config = ConfigWrapper(**config)
            for key, value in config.items():
                setattr(self, key, value)

    @inlineCallbacks
    def connect(self):
        if self.cxn is None:
            self.cxn = connection()  
            yield self.cxn.connect()
        self.context = yield self.cxn.context()
        yield self.getChannels()
        try:
            self.populate()
        except Exception as e:
            print(e)
        yield self.displaySequence(self.default_sequence)
        yield self.connectSignals()
        yield self.update_sequencer(None, True)

    @inlineCallbacks
    def getChannels(self):
        sequencer = yield self.cxn.get_server(self.sequencer_servername)
        channels = yield sequencer.get_channels()
        self.channels = json.loads(channels)
        
        self.analog_channels = {k: c for k, c in self.channels.items() 
                                     if c['channel_type'] == 'analog'}
        self.digital_channels = {k: c for k, c in self.channels.items() 
                                     if c['channel_type'] == 'digital'}
        self.electrode_channels = {k: c for k, c in self.channels.items()
                                     if c['channel_type'] == 'ad5791'}


        self.default_sequence = dict(
            [(nameloc, [{'type': 'lin', 'vf': 0, 'dt': 1}]) 
                  for nameloc in self.analog_channels]
            + [(nameloc, [{'dt': 1, 'out': 0}]) 
                  for nameloc in self.digital_channels]
            + [(nameloc, [{'type': 's', 'vf': 0, 'dt': 1}]) 
                  for nameloc in self.electrode_channels])

    @inlineCallbacks
    def connectSignals(self):
        sequencer = yield self.cxn.get_server(self.sequencer_servername)
        yield sequencer.signal__update(self.config.sequencer_update_id)
        yield sequencer.addListener(listener=self.update_sequencer, source=None,
                                    ID=self.sequencer_update_id)
        conductor = yield self.cxn.get_server(self.conductor_servername)
        yield conductor.signal__parameters_updated(self.config.conductor_update_id)
        yield conductor.addListener(listener=self.update_parameters, 
                                    source=None, ID=self.conductor_update_id)

    def populate(self):
        self.loadSaveRun = LoadSaveRun()

        self.addDltRow = AddDltRow(self.config)
        self.addDltRow.scrollArea = QtGui.QScrollArea()
        self.addDltRow.scrollArea.setWidget(self.addDltRow)
        self.addDltRow.scrollArea.setWidgetResizable(True)
        self.addDltRow.scrollArea.setHorizontalScrollBarPolicy(1)
        self.addDltRow.scrollArea.setVerticalScrollBarPolicy(1)
        self.addDltRow.scrollArea.setFrameShape(0)

        self.durationRow = DurationRow(self.config)
        self.durationRow.scrollArea = QtGui.QScrollArea()
        self.durationRow.scrollArea.setWidget(self.durationRow)
        self.durationRow.scrollArea.setWidgetResizable(True)
        self.durationRow.scrollArea.setHorizontalScrollBarPolicy(1)
        self.durationRow.scrollArea.setVerticalScrollBarPolicy(1)
        self.durationRow.scrollArea.setFrameShape(0)

        self.digitalControl = DigitalControl(self.digital_channels, self.config)
        self.analogControl = AnalogControl(self.analog_channels, self.config)
        self.electrodeControl = ElectrodeControl(self.electrode_channels, self.config)

        self.hscrollArray = QtGui.QScrollArea()
        self.hscrollArray.setWidget(QtGui.QWidget())
        self.hscrollArray.setHorizontalScrollBarPolicy(2)
        self.hscrollArray.setVerticalScrollBarPolicy(1)
        self.hscrollArray.setWidgetResizable(True)
        self.hscrollArray.setFrameShape(0)
        
        self.hscrollName = QtGui.QScrollArea()
        self.hscrollName.setWidget(QtGui.QWidget())
        self.hscrollName.setHorizontalScrollBarPolicy(2)
        self.hscrollName.setVerticalScrollBarPolicy(1)
        self.hscrollName.setWidgetResizable(True)
        self.hscrollName.setFrameShape(0)
        
        self.splitter = QtGui.QSplitter(QtCore.Qt.Vertical)
        self.splitter.addWidget(self.digitalControl)
        self.splitter.addWidget(self.analogControl)

        self.splitter_line = QtGui.QFrame()
        self.splitter_line.setFixedHeight(2)
        self.splitter_line.setFrameShape(QtGui.QFrame.HLine)
        self.splitter_line.setFrameShadow(QtGui.QFrame.Sunken)
        self.splitter.addWidget(self.splitter_line)

        self.splitter.addWidget(self.electrodeControl)

        #spacer widgets
        self.northwest = QtGui.QWidget()
        self.northeast = QtGui.QWidget()
        self.southwest = QtGui.QWidget()
        self.southeast = QtGui.QWidget()

        self.layout = QtGui.QGridLayout()
        self.layout.addWidget(self.northwest, 0, 0, 2, 1)
        self.layout.addWidget(self.loadSaveRun, 0, 1)
        self.layout.addWidget(self.northeast, 0, 2, 2, 1)
        self.layout.addWidget(self.durationRow.scrollArea, 1, 1)
        self.layout.addWidget(self.splitter, 2, 0, 1, 3)
        self.layout.addWidget(self.southwest, 3, 0, 1, 1)
        self.layout.addWidget(self.addDltRow.scrollArea, 3, 1)
        self.layout.addWidget(self.hscrollName, 4, 0)
        self.layout.addWidget(self.hscrollArray, 4, 1)
        self.layout.addWidget(self.southeast, 3, 2, 2, 1)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        self.setWindowTitle('sequencer control')

        self.setLayout(self.layout)
        self.setSizes()
        self.connectWidgets()

    def setSizes(self):
        self.northwest.setFixedSize(self.namecolumn_width, self.durationrow_height)
        self.loadSaveRun.setFixedWidth(10*self.spacer_width)
        self.northeast.setFixedSize(20, self.durationrow_height)
        
        for c in self.digitalControl.array.columns:
            for b in c.buttons.values():
                b.setFixedSize(self.spacer_width, self.spacer_height)
            # -1 because there is a generic widget in the last spot
            height = sum([c.layout.itemAt(i).widget().height() for i in range(c.layout.count()-1)]) 
            c.setFixedSize(self.spacer_width, height)
        da_width = sum([c.width() for c in self.digitalControl.array.columns if not c.isHidden()])
        da_height = self.digitalControl.array.columns[0].height()
        self.digitalControl.array.setFixedSize(da_width, da_height)

        for nl in self.digitalControl.nameColumn.labels.values():
            nl.setFixedHeight(self.spacer_height)
        nc_width = self.namelabel_width
        nc_height = self.digitalControl.array.height()
        self.digitalControl.nameColumn.setFixedSize(nc_width, nc_height)
        self.digitalControl.nameColumn.scrollArea.setFixedWidth(self.namecolumn_width)
        
        self.digitalControl.vscroll.widget().setFixedSize(0, self.digitalControl.array.height())
        self.digitalControl.vscroll.setFixedWidth(20)
        
        width = self.digitalControl.array.width()
        height = self.analog_height*len(self.analog_channels)
        self.analogControl.array.setFixedSize(width, height)
        self.analogControl.vscroll.widget().setFixedSize(0, self.analogControl.array.height())
        self.analogControl.vscroll.setFixedWidth(20)
        
        for nl in self.analogControl.nameColumn.labels.values():
            nl.setFixedSize(self.namelabel_width, self.analog_height)
        nc_width = self.namelabel_width
        nc_height = self.analogControl.array.height()
        self.analogControl.nameColumn.setFixedSize(nc_width, nc_height)
        self.analogControl.nameColumn.scrollArea.setFixedWidth(self.namecolumn_width)


        height = self.analog_height*len(self.electrode_channels)
        self.electrodeControl.array.setFixedSize(width, height)
        self.electrodeControl.vscroll.widget().setFixedSize(0, self.electrodeControl.array.height())
        self.electrodeControl.vscroll.setFixedWidth(20)

        for nl in self.electrodeControl.nameColumn.labels.values():
            nl.setFixedSize(self.namelabel_width, self.analog_height)
        nc_width = self.namelabel_width
        nc_height = self.electrodeControl.array.height()
        self.electrodeControl.nameColumn.setFixedSize(nc_width, nc_height)
        self.electrodeControl.nameColumn.scrollArea.setFixedWidth(self.namecolumn_width)
        
        for b in self.durationRow.boxes:
            b.setFixedSize(self.spacer_width, self.durationrow_height)
        dr_width = sum([db.width() for db in self.durationRow.boxes if not db.isHidden()])
        self.durationRow.setFixedSize(dr_width, self.durationrow_height)
        self.durationRow.scrollArea.setFixedHeight(self.durationrow_height)
       
        self.southwest.setFixedSize(self.namecolumn_width, self.durationrow_height)
        self.southeast.setFixedWidth(20)
        
        for b in self.addDltRow.buttons:
            b.setFixedSize(self.spacer_width, 15)
        self.addDltRow.setFixedSize(dr_width, self.durationrow_height)
        self.addDltRow.scrollArea.setFixedHeight(self.durationrow_height)
        
        self.hscrollArray.widget().setFixedSize(self.analogControl.array.width(), 0)
        self.hscrollArray.setFixedHeight(20)
        self.hscrollName.widget().setFixedSize(self.namelabel_width, 0)
        self.hscrollName.setFixedSize(self.namecolumn_width, 20)

    def connectWidgets(self):

        self.hscrollArray.horizontalScrollBar().valueChanged.connect(self.adjustForHScrollArray)
        self.hscrollName.horizontalScrollBar().valueChanged.connect(self.adjustForHScrollName)

        self.loadSaveRun.saveButton.clicked.connect(self.saveSequence)
        self.loadSaveRun.runButton.clicked.connect(self.runSequence)
        self.loadSaveRun.loadButton.clicked.connect(self.browse)

        for i, b in enumerate(self.addDltRow.buttons):
            b.add.clicked.connect(self.addColumn(i))
            b.dlt.clicked.connect(self.dltColumn(i))

        for l in self.digitalControl.nameColumn.labels.values():
            l.clicked.connect(self.onDigitalNameClick(l.nameloc))

        for l in self.analogControl.nameColumn.labels.values():
            l.clicked.connect(self.onAnalogNameClick(l.nameloc))

        for l in self.electrodeControl.nameColumn.labels.values():
            l.clicked.connect(self.onElectrodeNameClick(l.nameloc))

        # KM added below 05/07/18
        # for tracking changes
        for col in self.digitalControl.array.columns:
            for key, val in col.buttons.items():
                val.changed_signal.connect(self.sequenceChanged)
        for b in self.durationRow.boxes:
            b.changed_signal.connect(self.sequenceChanged)

    # Handle double click events
    # Open the description editor
    def mouseDoubleClickEvent(self, event):
        self.openDescriptionDialog() 

    # Opens dialog for adding annotations to the sequence
    def openDescriptionDialog(self):
        try:
            a = DescriptionDialog(self.getSequence(), self.metadata['descriptions'])
        except:
            a = DescriptionDialog(self.getSequence(), [''])

        if a.exec_():
            self.metadata['descriptions'] = a.getDescriptions()
            self.updateDescriptionTooltips()
            self.sequenceChanged()

    def updateDescriptionTooltips(self):
        for ad, b, dc, d in zip(self.addDltRow.buttons,
                                self.durationRow.boxes,
                                self.digitalControl.array.columns,
                                self.metadata['descriptions']):
            ad.setToolTip(str(d))
            b.setToolTip(str(d))
            dc.setToolTip(str(d))
        self.analogControl._setTooltips(self.metadata['descriptions'])
        self.electrodeControl._setTooltips(self.metadata['descriptions'])
#
#        self.analogControl.array.mouseover_col = -1
#        self.electrodeControl.array.mouseover_col = -1

    def onDigitalNameClick(self, channel_name):
        channel_name = str(channel_name)
        @inlineCallbacks
        def odnc():
            if QtGui.qApp.mouseButtons() & QtCore.Qt.RightButton:

                pass
#                # removed KM 03/18/18
#                # we don't use the manual mode, and it's dangerous to be able to enable it
#                server = yield self.cxn.get_server(self.sequencer_servername)
#                mode = yield server.channel_mode(channel_name)
#                if mode == 'manual':
#                    yield server.channel_mode(channel_name, 'auto')
#                else:
#                    yield server.channel_mode(channel_name, 'manual')
            elif QtGui.qApp.mouseButtons() & QtCore.Qt.LeftButton:
                server = yield self.cxn.get_server(self.sequencer_servername)
                state = yield server.channel_manual_output(channel_name)
                yield server.channel_manual_output(channel_name, not state)
        return odnc

    def onAnalogNameClick(self, channel_name):
        channel_name = str(channel_name)
        @inlineCallbacks
        def oanc():
            if QtGui.qApp.mouseButtons() & QtCore.Qt.RightButton:
                pass

#                # removed KM 03/18/18
#                # we don't use the manual mode, and it's dangerous to be able to enable it
#                conf = AnalogControlConfig()
#                conf.name = channel_name.split('@')[0]
#                widget = AnalogVoltageManualControl(conf, self.reactor)
#                dialog = QtGui.QDialog()
#                dialog.ui = widget
#                dialog.setAttribute(QtCore.Qt.WA_DeleteOnClose)
#                widget.show()
            elif QtGui.qApp.mouseButtons() & QtCore.Qt.LeftButton:
                ave_args = (channel_name, self.getSequence(), self.config, self.reactor, self.cxn)
                ave = AnalogVoltageEditor(*ave_args)
                if ave.exec_():
                    sequence = ave.getEditedSequence().copy()
                    self.displaySequence(sequence)

                    # added KM 05/07/2018
                    # star on the title bar for unsaved
                    self.sequenceChanged()
                conductor = yield self.cxn.get_server(self.conductor_servername)
                yield conductor.removeListener(listener=ave.receive_parameters, ID=ave.config.conductor_update_id)
        return oanc


    # def onStableNameClick(self, channel_name):
    #     channel_name = str(channel_name)
    #     @inlineCallbacks
    #     def osnc():
    #         if QtGui.qApp.mouseButtons() & QtCore.Qt.RightButton:
    #             pass
    #         elif QtGui.qApp.mouseButtons() & QtCore.Qt.LeftButton:
    #             ave_args = (channel_name, self.getSequence(), self.config, self.reactor, self.cxn)
    #             ave = ElectrodeEditor(*ave_args)
    #             if ave.exec_():
    #                 sequence = ave.getEditedSequence().copy()
    #                 self.displaySequence(sequence)

    #                 # added KM 05/07/2018
    #                 # star on the title bar for unsaved
    #                 self.sequenceChanged()
    #             conductor = yield self.cxn.get_server(self.conductor_servername)
    #             yield conductor.removeListener(listener=ave.receive_parameters, ID=ave.config.conductor_update_id)
    #     return osnc

    def onElectrodeNameClick(self, channel_name):
        channel_name = str(channel_name)
        @inlineCallbacks
        def oenc():
            if QtGui.qApp.mouseButtons() & QtCore.Qt.RightButton:
                pass
            elif QtGui.qApp.mouseButtons() & QtCore.Qt.LeftButton:
                try:
                    v = self.metadata['electrodes']
                except:
                    v = []
                ave_args = (self.electrode_channels, self.getSequence(), v, self.config, self.reactor, self.cxn)
                ave = ElectrodeEditor(*ave_args)
                if ave.exec_():
                    sequence = ave.getEditedSequence()

                    self.metadata['electrodes'] = deepcopy(ave.getElectrodeSequence())
                    self.displaySequence(sequence)

                    # added KM 05/07/2018
                    # star on the title bar for unsaved
                    self.sequenceChanged()
                conductor = yield self.cxn.get_server(self.conductor_servername)
                yield conductor.removeListener(listener=ave.receive_parameters, ID=ave.config.conductor_update_id)
                electrode = yield self.cxn.get_server(self.electrode_servername)
                yield electrode.removeListener(listener=ave._update_presets, ID=ave.config.electrode_update_id)
        return oenc


    def adjustForDVScroll(self):
        val = self.digitalVScroll.verticalScrollBar().value()
        self.digitalNameScroll.verticalScrollBar().setValue(val)
        self.digitalScroll.verticalScrollBar().setValue(val)
    
    def adjustForAVScroll(self):
        val = self.analogVScroll.verticalScrollBar().value()
        self.analogNameScroll.verticalScrollBar().setValue(val)
        self.analogArrayScroll.verticalScrollBar().setValue(val)

    def adjustForHScrollArray(self):
        val = self.hscrollArray.horizontalScrollBar().value()
        self.durationRow.scrollArea.horizontalScrollBar().setValue(val)
        self.digitalControl.array.scrollArea.horizontalScrollBar().setValue(val)
        self.analogControl.array.scrollArea.horizontalScrollBar().setValue(val)
        self.addDltRow.scrollArea.horizontalScrollBar().setValue(val)
    
    def adjustForHScrollName(self):
        val = self.hscrollName.horizontalScrollBar().value()
        self.digitalControl.nameColumn.scrollArea.horizontalScrollBar().setValue(val)
        self.analogControl.nameColumn.scrollArea.horizontalScrollBar().setValue(val)
    
    def browse(self):
        timestr = time.strftime(self.time_format)
        directory = self.sequence_directory.format(timestr)
        if os.path.exists(directory):
            directory = directory
        else:
            directory = self.sequence_directory.split('{}')[0]
        filepath = QtGui.QFileDialog().getOpenFileName(directory=directory)
        if filepath:
            self.loadSaveRun.locationBox.setText(filepath)
            self.loadSequence(filepath)
    
    def saveSequence(self):
        filename = self.loadSaveRun.locationBox.text().split(SEP)[-1]
        timestr = time.strftime(self.time_format)
        directory = self.sequence_directory.format(timestr)
        filepath = directory + filename
        if not os.path.exists(directory):
            os.makedirs(directory)
        with open(filepath, 'w+') as outfile:
            sequence = self.getSequence()
            toSave = {}
            toSave['sequence'] = sequence
            toSave['meta'] = self.metadata
            json.dump(toSave, outfile)

        self.setWindowTitle('sequencer control')

    @inlineCallbacks
    def runSequence(self, c):
        self.saveSequence()
        sequence = self.getSequence()

        # changed KM 05/07/2018
        seq_time = 0
        # get the total sequence time
        for k, d in sequence.items():
            for step in d:
            	seq_time += step['dt']
            break

        # if the sequence is longer than MIN_SEQ_TIME, run the sequence
        if seq_time >= MIN_SEQ_TIME:
            conductor = yield self.cxn.get_server(self.conductor_servername)
            sequence_json = json.dumps({'sequencer': {'sequence': [sequence]}})
            yield conductor.set_parameter_values(sequence_json)
        # otherwise, throw up a message box and don't run
        else:
            msg = QtGui.QMessageBox()
            msg.setIcon(QtGui.QMessageBox.Information)
            msg.setText("Sequences shorter than " + str(MIN_SEQ_TIME) + "s cannot be run from the sequencer control.")
            msg.setDetailedText("To change the minimum sequence time, change the variable MIN_SEQ_TIME at the top of sequencer_control.py.")
            msg.exec_()
    
    @inlineCallbacks
    def loadSequence(self, filepath):
        with open(filepath, 'r') as infile:
            sequence = json.load(infile)

        if 'sequence' in sequence:
            self.metadata = sequence['meta']

            if 'descriptions' not in self.metadata:
                v = sequence['sequence'][self.config.timing_channel]
                self.metadata['descriptions'] = ['']*len(v)
            if 'electrodes' not in self.metadata:
                v = sequence['sequence'][self.config.timing_channel]
                self.metadata['electrodes'] = [zero_sequence(x['dt']) for x in v]
            sequence = sequence['sequence']
        else:
            v = sequence[self.config.timing_channel]
            self.metadata['descriptions'] = ['']*len(v)
            self.metadata['electrodes'] = [zero_sequence(x['dt']) for x in v]

        self.updateDescriptionTooltips()

        sequencer = yield self.cxn.get_server(self.sequencer_servername)
        sequence = yield sequencer.fix_sequence_keys(json.dumps(sequence))
        self.displaySequence(json.loads(sequence))
        self.loadSaveRun.locationBox.setText(filepath)

        self.setWindowTitle('sequencer control')

    @inlineCallbacks
    def displaySequence(self, sequence):
        self.sequence = sequence
        self.durationRow.displaySequence(sequence)
        self.digitalControl.displaySequence(sequence)
        self.analogControl.displaySequence(sequence)
        self.electrodeControl.displaySequence(sequence)
        self.addDltRow.displaySequence(sequence)
        yield self.updateParameters()
    
    @inlineCallbacks
    def updateParameters(self):
        parameters = {'sequencer': get_sequence_parameters(self.sequence)}
        parameters_json = json.dumps(parameters)
        conductor = yield self.cxn.get_server(self.conductor_servername)
        pv_json = yield conductor.get_parameter_values(parameters_json, True)
        parameter_values = json.loads(pv_json)['sequencer']
        self.durationRow.updateParameters(parameter_values)
        self.digitalControl.updateParameters(parameter_values)
        self.analogControl.updateParameters(parameter_values)
        self.electrodeControl.updateParameters(parameter_values)
        self.addDltRow.updateParameters(parameter_values)
        self.setSizes()

    @inlineCallbacks
    def update_parameters(self, c, signal):
        if signal:
            yield self.updateParameters()

    @inlineCallbacks
    def update_sequencer(self, c, signal):
        if signal:
            sequencer = yield self.cxn.get_server(self.sequencer_servername)
            channels = yield sequencer.get_channels()
            for l in self.digitalControl.nameColumn.labels.values():
                l.displayModeState(json.loads(channels)[l.nameloc])
    
    def getSequence(self):
        durations = [b.value() for b in self.durationRow.boxes 
                if not b.isHidden()]
        digital_logic = [c.getLogic() 
                for c in self.digitalControl.array.columns 
                if not c.isHidden()]
        digital_sequence = {key: [{'dt': dt, 'out': dl[key]} 
                for dt, dl in zip(durations, digital_logic)]
                for key in self.digital_channels}
        analog_sequence = {key: [dict(s.items() + {'dt': dt}.items()) 
                for s, dt in zip(self.analogControl.sequence[key], durations)]
                for key in self.analog_channels}
        electrode_sequence = {key: [dict(s.items() + {'dt': dt}.items()) 
                for s, dt in zip(self.electrodeControl.sequence[key], durations)]
                for key in self.electrode_channels}

        # Make sure the durations in metadata['electrodes'] are updated!
        for i, data in enumerate(self.metadata['electrodes']):
            data.update({'dt': durations[i]})
        sequence = dict(digital_sequence.items() + analog_sequence.items() + electrode_sequence.items())
        return sequence
    
    def sequenceChanged(self):
        self.setWindowTitle('sequencer control*')

    def addColumn(self, i):
        def ac():
            sequence = self.getSequence()
            for c in self.channels:
                sequence[c].insert(i, sequence[c][i])
            self.displaySequence(sequence)

            self.metadata['descriptions'].insert(i, '')
            self.metadata['electrodes'].insert(i, deepcopy(self.metadata['electrodes'][i]))
            self.updateDescriptionTooltips()
        return ac

    def dltColumn(self, i):
        def dc():
            sequence = self.getSequence()
            for c in self.channels:
                sequence[c].pop(i)
            self.displaySequence(sequence)

            self.metadata['descriptions'].pop(i)
            self.metadata['electrodes'].pop(i)
            self.updateDescriptionTooltips()
        return dc

    def undo(self):
        pass
        #self.updateParameters()

    def redo(self):
        pass
        #self.updateParameters()

    def keyPressEvent(self, c):
        super(SequencerControl, self).keyPressEvent(c)
        if QtGui.QApplication.keyboardModifiers() == QtCore.Qt.ControlModifier:
            if c.key() == QtCore.Qt.Key_Z:
                self.undo()
            if c.key() == QtCore.Qt.Key_R:
                self.redo()
            if c.key() == QtCore.Qt.Key_S:
                self.saveSequence()
            if c.key() == QtCore.Qt.Key_Return:
                self.runSequence(c)
            if c.key() in [QtCore.Qt.Key_Q, QtCore.Qt.Key_W]:
                self.reactor.stop()
            if c.key() == QtCore.Qt.Key_B:
                self.browse()

    def closeEvent(self, x):
        self.reactor.stop()

if __name__ == '__main__':
    a = QtGui.QApplication([])
    import qt4reactor 
    qt4reactor.install()
    from twisted.internet import reactor
    widget = SequencerControl(reactor)
    widget.setWindowIcon(QtGui.QIcon('./lib/sq.png'))
    widget.show()
    reactor.run() 
