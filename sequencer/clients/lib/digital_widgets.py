from PyQt4 import QtGui, QtCore, Qt
from PyQt4.QtCore import pyqtSignal
import numpy as np
import json
import matplotlib
from twisted.internet.defer import inlineCallbacks
matplotlib.use('Qt4Agg')

import helpers

import sys
sys.path.append('../../../client_tools')
from connection import connection

class DigitalVariableSelector(QtGui.QInputDialog):
    def __init__(self, variables):
        super(DigitalVariableSelector, self).__init__()
        self.setWindowTitle('TTL variable selection')
        self.setLabelText('Variable: ')
        
        self.variables = variables
        self.populate()

    def populate(self):
        self.setComboBoxItems(self.variables)
        self.setComboBoxEditable(True)

class Spacer(QtGui.QFrame):
    def __init__(self, config):
        super(Spacer, self).__init__(None)
        self.setFixedSize(config.spacer_width, config.spacer_height)
        self.setFrameShape(1)
        self.setLineWidth(0)

class SequencerButton(QtGui.QLabel):
    # added KM 05/07/18
    changed_signal = QtCore.pyqtSignal()
    # added KM 1/23/19
    # payload is (mouse_button_clicked, sequencer_button_nameloc)
    # button_clicked: 1 = Left, 2 = Right
    clicked_signal = QtCore.pyqtSignal(int,str)

    def __init__(self):
        super(SequencerButton, self).__init__(None)
        self.setFrameShape(2)
        self.setLineWidth(1)
        self.on_color = '#ff69b4'
        self.off_color = '#ffffff'
        self.name = ''
        self.variable = None
        
    def setChecked(self, state):
        if state:
            self.setFrameShadow(0x0030)
            self.setStyleSheet('QWidget {background-color: %s}' % self.on_color)
            self.is_checked = True
        else:
            self.setFrameShadow(0x0020)
            self.setStyleSheet('QWidget {background-color: %s}' % self.off_color)
            self.is_checked = False
        # added KM 05/07/18
        self.changed_signal.emit()

    def changeState(self):
        if self.is_checked:
            self.setChecked(False)
        else:
            self.setChecked(True)

    # modified KM 1/23/19
    def mousePressEvent(self, event):
        # 1 is Left, 2 is Right click
        mouse_button = event.button()
        
        if mouse_button == 1:
            if self.variable is not None:
                event.accept()
                return 
            self.changeState()
        self.clicked_signal.emit(mouse_button, self.name)
        event.accept()

    # TODO: Call this when the variable is set via the dialog
    def setVariable(self, variable=None):
        self.variable = variable
        if variable is not None:
            self.setText(self.variable)
        else:
            self.setText("")

    def getVariable(self):
        return self.variable

class DigitalColumn(QtGui.QWidget):

    # added KM 1/23/19
    # payload: (mouse_button_clicked, sequence_button_nameloc, column_index)
    clicked_signal = pyqtSignal(int,str,int)

    def __init__(self, channels, config, position):
        super(DigitalColumn, self).__init__(None)
        self.channels = channels
        self.config = config
        self.position = position
        self.populate()

    def populate(self):
        self.buttons = {nl: SequencerButton() for nl in self.channels}

        # added KM 1/23/19
        for (nl, b) in self.buttons.items():
            b.name = nl
            b.clicked_signal.connect(self.handle_click)

        self.layout = QtGui.QVBoxLayout()
        self.layout.setSpacing(0)
        self.layout.setContentsMargins(0, 0, 0, 0)
        for i, nl in enumerate(sorted(self.channels, key=lambda nl: nl.split('@')[1])):
            if not i%16 and i != 0:
                self.layout.addWidget(Spacer(self.config))
            self.layout.addWidget(self.buttons[nl])
            self.buttons[nl].on_color = self.config.digital_colors[i%len(self.config.digital_colors)]
        self.layout.addWidget(QtGui.QWidget())
        self.setLayout(self.layout)

    def getLogic(self):
        return {nl: int(self.buttons[nl].is_checked) for nl in self.channels}

    def setLogic(self, sequence):
        for nameloc in self.channels:
            self.buttons[nameloc].setChecked(sequence[nameloc][self.position]['out'])

    # added KM 1/23/19
    def handle_click(self, mouse_button, nl):
        self.clicked_signal.emit(mouse_button, nl, self.position)

class DigitalArray(QtGui.QWidget):

    # added KM 1/23/19
    shift_toggled = False
    toggle_sign = False
    last_clicked = {'nl': '', 'column': 0, 'mouse_button': 1}

    # Payload is nameloc, column
    variable_changed = pyqtSignal(str, int)

    def __init__(self, channels, config):
        super(DigitalArray, self).__init__(None)
        self.channels = channels
        self.config = config
        self.populate()

        # added KM 1/23/19
        self.setFocusPolicy(QtCore.Qt.ClickFocus)
        for col in self.columns:
            col.clicked_signal.connect(self.handle_click)

        self.channel_to_index = {}
        self.index_to_channel = []
        for i, nl in enumerate(sorted(self.channels, key=lambda nl: nl.split('@')[1])):
            self.channel_to_index[nl] = i
            self.index_to_channel.append(nl)

    def populate(self):
        self.columns = [DigitalColumn(self.channels, self.config, i) for i in range(self.config.max_columns)]
        self.layout = QtGui.QHBoxLayout()
        for lc in self.columns:
            self.layout.addWidget(lc)
        self.layout.setSpacing(0)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout)

    def displaySequence(self, sequence): 
        shown_columns = sum([1 for c in self.columns if not c.isHidden()])
        num_to_show = len(sequence[self.config.timing_channel])
        if shown_columns > num_to_show:
            for c in self.columns[num_to_show: shown_columns][::-1]:
                c.hide()
        elif shown_columns < num_to_show:
            for c in self.columns[shown_columns:num_to_show]:
                c.show()
        for c in self.columns[:num_to_show]:
            c.setLogic(sequence)

    # added KM 1/23/19
    # watches for shift key depressed
    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Shift:
            self.shift_toggled = True
        else:
            super(DigitalArray, self).keyPressEvent(event)

    # added KM 1/23/19
    # watches for shift key released
    def keyReleaseEvent(self, event):
        if event.key() == QtCore.Qt.Key_Shift:
            self.shift_toggled = False
        else:
            super(DigitalArray, self).keyPressEvent(event)

    def get_button_ranges(self, first, first_nl, last, last_nl):
        first_index = self.channel_to_index[first_nl]
        last_index = self.channel_to_index[last_nl]
        
        # generate array of indices so we can grab every sequencer button
        # between the two that were clicked
        channel_index = range(min(first_index, last_index), max(first_index, last_index) + 1)
        col_index = range(min(first, last), max(first, last) + 1)

        return (col_index, channel_index)

    def buttons_from_ranges(self, col_index, channel_index):
        return [self.columns[i].buttons[self.index_to_channel[j]] for (i,j) in [(i,j) for i in col_index for j in channel_index]]

    def poll_and_change_state(self, buttons):
        # take a poll to determine what sign to set the buttons to
        poll = 0
        for b in buttons:
            if b.getVariable() is None:
                if b.is_checked:
                    poll += 1
                else: 
                    poll -= 1
        state = False if poll > 0 else True
        
        for b in buttons:
            if b.getVariable() is None:
                b.setChecked(state)
        
    # added KM 1/23/19
    # receives signals for clicks on the sequencer buttons
    # changes state of entire intermediate region when shift is depressed
    def handle_click(self, mouse_button, nl, column):
        nl = str(nl) # name loc of currently clicked channel
        last_nl = self.last_clicked['nl']
        last_column = self.last_clicked['column']
        last_mouse_button = self.last_clicked['mouse_button']

        # look for shift toggled
        if self.shift_toggled and last_mouse_button == mouse_button:
            clicked_buttons = (
                self.columns[last_column].buttons[last_nl], # Previously clicked button
                self.columns[column].buttons[nl] # Most recently clicked
            )

            # Get all buttons contained in the rectangle with edges defined by clicked_buttons
            buttons = self.buttons_from_ranges(
                *self.get_button_ranges(last_column, last_nl, column, nl)
            )

            if mouse_button == 1: # Left click
                # flip one of the two buttons state for fairness in the poll
                clicked_buttons[0].setChecked(not clicked_buttons[0].is_checked)
                self.poll_and_change_state(buttons)

            elif mouse_button == 2: # Right click
                prev_variable = clicked_buttons[0].getVariable()

                # Two interaction patterns:
                # If the previously clicked button has a variable,
                # then by shift-clicking we are trying to set the variable in every intermediate button.
                # Otherwise, we are trying to clear the variable in every intermediate button.
                # Both are handled by the following loop
                for b in buttons:
                    b.setChecked(False)
                    b.setVariable(prev_variable)
        else:
            if mouse_button == 2:
                clicked_button = self.columns[column].buttons[nl]

                if clicked_button.getVariable() is None:
                    clicked_button.setChecked(False)
                    self.variable_changed.emit(nl, column)
                else:
                    clicked_button.setVariable(None)

        # Update what the last clicked button is
        self.last_clicked = {'nl': nl, 'column': column, 'mouse_button': mouse_button}

    def set_button_variable(self, nl, column, variable):
        self.columns[column].buttons[nl].setVariable(variable)

class NameBox(QtGui.QLabel):
    clicked = QtCore.pyqtSignal()
    def __init__(self, nameloc):
        super(NameBox, self).__init__(None)
        self.nameloc = nameloc
        name, loc = nameloc.split('@')
        self.setText(loc+': '+name)
        self.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter  )
        self.name = name
        self.off_color = '#ffffff'
        self.auto_color = '#dddddd'

    def mousePressEvent(self, x):
        self.clicked.emit()

    def displayModeState(self, x):
        if x['mode'] == 'manual':
            if x['manual_output']:
                self.setStyleSheet('QWidget {background-color: %s}' % self.on_color)
            else:
                self.setStyleSheet('QWidget {background-color: %s}' % self.off_color)
        else:
            self.setStyleSheet('QWidget {background-color: %s}' % self.auto_color)


class DigitalNameColumn(QtGui.QWidget):
    def __init__(self, channels, config):
        super(DigitalNameColumn, self).__init__(None)
        self.channels = channels
        self.config = config
        self.populate()

    def populate(self):
        self.labels = {nl: NameBox(nl) for nl in self.channels}
        self.layout = QtGui.QVBoxLayout()
        self.layout.setSpacing(0)
        self.layout.setContentsMargins(10, 0, 0, 0)
        for i, nl in enumerate(sorted(self.channels, key=lambda nl: nl.split('@')[1])):
            if not i%16 and i != 0:
                self.layout.addWidget(Spacer(self.config))
            self.layout.addWidget(self.labels[nl])
            self.labels[nl].on_color = self.config.digital_colors[i%len(self.config.digital_colors)]
        self.layout.addWidget(QtGui.QWidget())
        self.setLayout(self.layout)

class DigitalControl(QtGui.QWidget):
    def __init__(self, channels, config):
        super(DigitalControl, self).__init__(None)
        self.channels = channels
        self.config = config
        self.populate()

    def populate(self):
        self.nameColumn = DigitalNameColumn(self.channels, self.config)
        self.nameColumn.scrollArea = QtGui.QScrollArea()
        self.nameColumn.scrollArea.setWidget(self.nameColumn)
        self.nameColumn.scrollArea.setWidgetResizable(True)
        self.nameColumn.scrollArea.setHorizontalScrollBarPolicy(1)
        self.nameColumn.scrollArea.setVerticalScrollBarPolicy(1)
        self.nameColumn.scrollArea.setFrameShape(0)

        self.array = DigitalArray(self.channels, self.config)
        self.array.scrollArea = QtGui.QScrollArea()
        self.array.scrollArea.setWidget(self.array)
        self.array.scrollArea.setWidgetResizable(True)
        self.array.scrollArea.setHorizontalScrollBarPolicy(1)
        self.array.scrollArea.setVerticalScrollBarPolicy(1)
        self.array.scrollArea.setFrameShape(0)

        self.vscroll = QtGui.QScrollArea()
        self.vscroll.setWidget(QtGui.QWidget())
        self.vscroll.setHorizontalScrollBarPolicy(1)
        self.vscroll.setVerticalScrollBarPolicy(2)
        self.vscroll.setFrameShape(0)
        
        self.layout = QtGui.QHBoxLayout()
        self.layout.addWidget(self.nameColumn.scrollArea)
        self.layout.addWidget(self.array.scrollArea)
        self.layout.addWidget(self.vscroll)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        self.setLayout(self.layout)

        self.connectWidgets()
    
    def displaySequence(self, sequence):
        self.array.displaySequence(sequence)

    def updateParameters(self, parameter_values):
        pass
    
    def connectWidgets(self):
        self.vscrolls = [self.nameColumn.scrollArea.verticalScrollBar(),
                self.array.scrollArea.verticalScrollBar(),
                self.vscroll.verticalScrollBar()]
        for vs in self.vscrolls:
            vs.valueChanged.connect(self.adjust_for_vscroll(vs))
    
    def adjust_for_vscroll(self, scrolled):
        def afv():
            val = scrolled.value()
            for vs in self.vscrolls:
                vs.setValue(val)
        return afv

