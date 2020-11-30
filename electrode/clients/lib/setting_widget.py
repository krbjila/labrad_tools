from __future__ import absolute_import
import json
import time
import numpy as np
import os
import sys

from copy import deepcopy

from PyQt4 import QtGui, QtCore, Qt
from PyQt4.QtCore import pyqtSignal 
from twisted.internet.defer import inlineCallbacks

sys.path.append('./settings/')
from setting_controls import SettingControl
from .helpers import json_loads_byteified

SEP = os.path.sep

class SettingWidget(QtGui.QWidget):
	settingChangedSignal = pyqtSignal()
	newSettingSignal = pyqtSignal()
	saveSettingSignal = pyqtSignal()
	updateDescriptionSignal = pyqtSignal()
	settingDeletedSignal = pyqtSignal(int)
	refreshSignal = pyqtSignal()

	def __init__(self, cxn=None):

		super(SettingWidget, self).__init__()
		self.cxn = cxn
		self.setFixedWidth(500)
		self.populate()

		self.currentSetting = 0
		self.connectSignals()

	def populate(self):
		self.layout = QtGui.QGridLayout()

		self.settingLabel = QtGui.QLabel("Setting")
		self.settingControl = SettingControl()

		self.descriptionLabel = QtGui.QLabel("Description")
		self.descriptionEdit = QtGui.QLineEdit()

		self.saveButton = QtGui.QPushButton("Save")
		self.deleteButton = QtGui.QPushButton("Delete")
		self.refreshButton = QtGui.QPushButton("Refresh")
		self.refreshButton.setToolTip("Force the electrode server to refresh values from config file")

		self.layout.addWidget(self.saveButton, 0, 3, 1, 1)
		self.layout.addWidget(self.deleteButton, 0, 4, 1, 1)
		self.layout.addWidget(self.refreshButton, 1, 4, 1, 1)

		self.layout.addWidget(self.settingLabel, 0, 0, 1, 1)
		self.layout.addWidget(self.settingControl, 0, 1, 1, 2)

		self.layout.addWidget(self.descriptionLabel, 1, 0, 1, 1)
		self.layout.addWidget(self.descriptionEdit, 1, 1, 1, 3)

		self.setLayout(self.layout)

	def setPresets(self, presets):
		self.presets = presets
		self.settingControl.setSettings(self.presets)
		self.settingChanged(0)

	def connectSignals(self):
		self.settingControl.activated.connect(self.comboBoxChanged)
		self.descriptionEdit.editingFinished.connect(self.updateDescription)
		self.saveButton.pressed.connect(self.saveSetting)
		self.deleteButton.pressed.connect(self.deleteSetting)
		self.refreshButton.pressed.connect(self.refresh)

	def refresh(self):
		self.refreshSignal.emit()

	def comboBoxChanged(self, index):
		if index < len(self.presets):
			self.settingChanged(index)
		else:
			self.newSetting(index)

	def settingChanged(self, index):
		# Just change description
		self.currentSetting = index
		self.descriptionEdit.setText(self.presets[index]['description'])
		self.settingChangedSignal.emit()


	def newSetting(self, index):
		# Open a dialog for new setting ID
		a = QtGui.QInputDialog()
		(newPresetID, ret) = a.getInt(None, "New Setting", "New setting ID: ", 1, 0)
		unique = self.validateNewID(newPresetID)

		# Repeat until we get a unique ID or the user cancels
		while ret and not unique:
			a = QtGui.QInputDialog()
			(newPresetID, ret) = a.getInt(None, "New Setting", "New setting ID: ", 1, 0)
			unique = self.validateNewID(newPresetID)

		# If user selects "Ok"
		if ret:
			newPreset = deepcopy(self.presets[self.currentSetting])
			newPreset['id'] = newPresetID
			newPreset['description'] = ''
			self.presets.append(newPreset)

			self.descriptionEdit.setText(newPreset['description'])

			self.settingControl.setItemText(index, "{}: {}".format(int(newPreset['id']), newPreset['description']))
			self.settingControl.addItem("New...")

			self.currentSetting = index
			self.settingControl.setCurrentIndex(self.currentSetting)

			self.newSettingSignal.emit()
		else:
			self.settingControl.setCurrentIndex(self.currentSetting)

	def validateNewID(self, idn):
		for x in self.presets:
			if x['id'] == idn:
				return False
		return True

	def updateDescription(self):
		self.presets[self.currentSetting]['description'] = str(self.descriptionEdit.text())
		current = self.presets[self.currentSetting]
		self.settingControl.setItemText(self.currentSetting, "{}: {}".format(int(current['id']), current['description']))
		self.updateDescriptionSignal.emit()

	def saveSetting(self):
		self.saveSettingSignal.emit()

	def deleteSetting(self):
		current = self.presets[self.currentSetting]

		msgBox = QtGui.QMessageBox()
		msgBox.setText("Do you really want to delete this?")
		msgBox.setInformativeText("Setting {}: {}".format(int(current['id']), current['description']))
		msgBox.setStandardButtons(QtGui.QMessageBox.Yes | QtGui.QMessageBox.Cancel)
		msgBox.setDefaultButton(QtGui.QMessageBox.Cancel)
		ret = msgBox.exec_()

		if ret == QtGui.QMessageBox.Yes:
			self.settingDeletedSignal.emit(self.currentSetting)

			# Set form to a default
			self.settingControl.removeItem(self.currentSetting)
			self.settingControl.setCurrentIndex(0)
			self.currentSetting = 0
			self.settingChanged(0)