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


# Copied from https://stackoverflow.com/a/52617714
class CollapsibleBox(QtGui.QWidget):
    def __init__(self, title="", parent=None):
        super(CollapsibleBox, self).__init__(parent)

        self.toggle_button = QtGui.QToolButton(
            text=title, checkable=True, checked=False
        )
        self.toggle_button.setStyleSheet("QToolButton { border: none; }")
        self.toggle_button.setToolButtonStyle(
            QtCore.Qt.ToolButtonTextBesideIcon
        )
        self.toggle_button.setArrowType(QtCore.Qt.RightArrow)
        self.toggle_button.pressed.connect(self.on_pressed)

        self.toggle_animation = QtCore.QParallelAnimationGroup(self)

        self.content_area = QtGui.QScrollArea(maximumHeight=0, minimumHeight=0)
        self.content_area.setSizePolicy(
            QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Fixed
        )
        self.content_area.setFrameShape(QtGui.QFrame.NoFrame)

        lay = QtGui.QVBoxLayout(self)
        lay.setSpacing(0)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.toggle_button)
        lay.addWidget(self.content_area)

        self.toggle_animation.addAnimation(
            QtCore.QPropertyAnimation(self, b"minimumHeight")
        )
        self.toggle_animation.addAnimation(
            QtCore.QPropertyAnimation(self, b"maximumHeight")
        )
        self.toggle_animation.addAnimation(
            QtCore.QPropertyAnimation(self.content_area, b"maximumHeight")
        )

    @QtCore.pyqtSlot()
    def on_pressed(self):
        checked = self.toggle_button.isChecked()
        self.toggle_button.setArrowType(
            QtCore.Qt.DownArrow if not checked else QtCore.Qt.RightArrow
        )
        self.toggle_animation.setDirection(
            QtCore.QAbstractAnimation.Forward
            if not checked
            else QtCore.QAbstractAnimation.Backward
        )
        self.toggle_animation.start()

    def setContentLayout(self, layout):
        lay = self.content_area.layout()
        del lay
        self.content_area.setLayout(layout)
        collapsed_height = (
            self.sizeHint().height() - self.content_area.maximumHeight()
        )
        content_height = layout.sizeHint().height()
        for i in range(self.toggle_animation.animationCount()):
            animation = self.toggle_animation.animationAt(i)
            animation.setDuration(500)
            animation.setStartValue(collapsed_height)
            animation.setEndValue(collapsed_height + content_height)

        content_animation = self.toggle_animation.animationAt(
            self.toggle_animation.animationCount() - 1
        )
        content_animation.setDuration(500)
        content_animation.setStartValue(0)
        content_animation.setEndValue(content_height)


class SequencerBoard(CollapsibleBox):
	shift_toggled = False
	last_clicked = 0
	any_changed = pyqtSignal()

	def __init__(self, board, channels, board_type):
		if board_type == 'digital':
			super(SequencerBoard, self).__init__(board)
		else:
			s = sorted(channels.keys(), key=lambda k: int(k.split('DAC')[1].split(':')[0]))
			super(SequencerBoard, self).__init__(s[0].split(':')[0] + ' - ' + s[-1].split(':')[0])

		self.channels = channels
		self.type = board_type

		self.populate()

	def populate(self):
		self.layout = QtGui.QVBoxLayout()

		self.channel_widgets = []

		for k in sorted(self.channels.keys(), key=lambda k: k.split('@')[1]):
			c = SequencerChannel(k.split('@')[1], self.channels[k], self.type)
			c.clicked_signal.connect(self.handleClick)
			self.channel_widgets.append(c)
			self.layout.addWidget(c)

		self.setContentLayout(self.layout)

	def handleClick(self, pos):
		if self.shift_toggled:
			start = min(self.last_clicked, pos)
			stop = max(self.last_clicked, pos)

			# Poll the boxes to know which state to set
			poll = 0
			for c in self.channel_widgets[start+1:stop]:
				if c.checkbox.isChecked():
					poll += 1
				else:
					poll -= 1

			# Buttons at start and stop have already been toggled
			# So count them oppositely in the poll
			for x in [start, stop]:
				if self.channel_widgets[x].checkbox.isChecked():
					poll -= 1
				else:
					poll += 1

			# Set the checkboxes to reverse the majority response
			for c in self.channel_widgets[start:stop+1]:
				if poll >= 0:
					c.checkbox.setChecked(False)
				else:
					c.checkbox.setChecked(True)
		self.last_clicked = pos
		self.any_changed.emit()

	# watches for shift key depressed
	def keyPressEvent(self, event):
		if event.key() == QtCore.Qt.Key_Shift:
			self.shift_toggled = True
		super(SequencerBoard, self).keyPressEvent(event)

	# watches for shift key released
	def keyReleaseEvent(self, event):
		if event.key() == QtCore.Qt.Key_Shift:
			self.shift_toggled = False
		super(SequencerBoard, self).keyPressEvent(event)

	def uncheckAll(self):
		for c in self.channel_widgets:
			c.checkbox.setChecked(False)

	def getCheckedChannels(self):
		return [c.key for c in self.channel_widgets if c.checkbox.isChecked()]


class SequencerChannel(QtGui.QWidget):
	clicked_signal = pyqtSignal(int)

	def __init__(self, channel_name, channel_data, channel_type):
		super(SequencerChannel, self).__init__()
		self.name = channel_name
		self.type = channel_type

		for key, val in channel_data.items():
			setattr(self, key, val)

		self.populate()

	def populate(self):
		self.layout = QtGui.QHBoxLayout()

		self.checkbox = QtGui.QCheckBox()
		self.checkbox.clicked.connect(self.clicked_action)
		self.checkbox.setTristate(False)

		if self.type == 'digital':
			self.label = QtGui.QLabel(self.loc + ': ' + self.name)
		else:
			self.label = QtGui.QLabel(self.name)
		self.label.setAlignment(QtCore.Qt.AlignLeft)

		self.layout.addWidget(self.checkbox)
		self.layout.addWidget(self.label)

		self.setLayout(self.layout)

	def clicked_action(self):
		# self.loc[-2:] is the channel number
		self.clicked_signal.emit(int(self.loc[-2:]))
