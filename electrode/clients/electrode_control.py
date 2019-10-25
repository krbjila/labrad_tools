import json
import time
import numpy as np
import os
import sys

from PyQt4 import QtGui, QtCore, Qt
from PyQt4.QtCore import pyqtSignal 
from twisted.internet.defer import inlineCallbacks

sys.path.append('./lib/')
sys.path.append('./lib/forms')
sys.path.append('./lib/settings')
sys.path.append('./lib/displays')
sys.path.append('./lib/efield')

from form_widget import FormWidget
from setting_widget import SettingWidget
from display_widget import DisplayWidget 
from calculator import ECalculator

from helpers import json_loads_byteified
from gui_defaults_helpers import DACsToVs, VsToDACs

sys.path.append('../../client_tools')
from connection import connection
SERVERNAME = "electrode"

SEP = os.path.sep
fit_coeffs_path = './lib/efield/comsol/data/fit_coeffs.json'

WIDGET_GEOMETRY = {
	'w' : 1600,
	'h' : 800
}

CXN_ID = 10101

class ElectrodeControl(QtGui.QWidget):
	def __init__(self, reactor, cxn=None):
		super(ElectrodeControl, self).__init__()
		self.reactor = reactor
		self.cxn = cxn

		self.calculator = ECalculator(fit_coeffs_path)

		self.setFixedWidth(WIDGET_GEOMETRY['w'])
		self.setFixedHeight(WIDGET_GEOMETRY['h'])

		self.populate()
		self.connect_to_labrad()

	def populate(self):
		self.setWindowTitle("Electrode Control")
		self.layout = QtGui.QVBoxLayout()

		self.settings = SettingWidget()
		self.forms = FormWidget(self.calculator)
		self.displays = DisplayWidget(self.calculator)

		self.forms.inputForms.crossUpdated.connect(self.inputFormChanged)
		self.settings.updateDescriptionSignal.connect(self.descriptionChanged)

		self.settings.settingChangedSignal.connect(self.settingChanged)
		self.settings.newSettingSignal.connect(self.newSettingAdded)
		self.settings.saveSettingSignal.connect(self.saveSetting)
		self.settings.settingDeletedSignal.connect(self.settingDeleted)
		self.settings.refreshSignal.connect(self.refresh)

		self.layout.addWidget(self.settings)
		self.layout.addWidget(self.forms)
		self.layout.addWidget(self.displays)

		font = QtGui.QFont()
		font.setPointSize(12)
		self.setFont(font)

		self.setLayout(self.layout)

	@inlineCallbacks
	def connect_to_labrad(self):
		if self.cxn is None:
			self.cxn = connection()  
			yield self.cxn.connect()
		self.context = yield self.cxn.context()
		self.server = yield self.cxn.get_server(SERVERNAME)

		yield self.server.signal__presets_changed(CXN_ID)
		yield self.server.addListener(listener=self._refresh, source=None, ID=CXN_ID)
		self.getPresets()

	@inlineCallbacks
	def getPresets(self):
		s = yield self.server.get_presets()
		self.presets = json_loads_byteified(s)
		self.settings.setPresets(self.presets)

	def descriptionChanged(self):
		self.presets[self.settings.currentSetting]['description'] = str(self.settings.descriptionEdit.text())
		self.unsavedChanges()

	def inputFormChanged(self):
		(vals, comp_shim) = self.forms.getValues()
		dac = VsToDACs(vals)
		self.presets[self.settings.currentSetting]['values'] = dac
		self.presets[self.settings.currentSetting]['compShim'] = comp_shim
		self.displays.setValues(vals, comp_shim)
		self.unsavedChanges()

	def unsavedChanges(self):
		self.setWindowTitle("Electrode Control*")

	def savedChanges(self):
		self.setWindowTitle("Electrode Control")

	@inlineCallbacks
	def saveSetting(self):
		yield self.server.update_presets(json.dumps(self.presets))
		self.savedChanges()

	def newSettingAdded(self):
	# 	# Because of aliasing between self.presets and self.settings.presets, following (commented) line is not necessary
	# 	self.presets.append(self.settings.presets[-1])
		self.settingChanged()

	def settingChanged(self):
		vs = self.presets[self.settings.currentSetting]['values']
		comp_shim = self.presets[self.settings.currentSetting]['compShim']
		vals = DACsToVs(vs)
		self.forms.setValues(vals, comp_shim)
		self.displays.setValues(vals, comp_shim)

	def settingDeleted(self, index):
		self.presets.pop(index)
		self.unsavedChanges()

	@inlineCallbacks
	def _refresh(self, x):
		yield self.refresh()

	@inlineCallbacks
	def refresh(self):
		yield self.server.reload_presets()
		self.getPresets()



if __name__ == '__main__':
    a = QtGui.QApplication([])
    a.setQuitOnLastWindowClosed(True)

    import qt4reactor 
    qt4reactor.install()
    from twisted.internet import reactor
    widget = ElectrodeControl(reactor)

    widget.show()
    reactor.run() 
