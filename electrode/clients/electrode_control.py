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
from optimize_dialog import OptimizationDialog

from helpers import json_loads_byteified
from gui_defaults_helpers import DACsToVs, VsToDACs, VsToNormalModes

sys.path.append('../../client_tools')
from connection import connection
SERVERNAME = "electrode"

SEP = os.path.sep
fit_coeffs_path = './lib/efield/comsol/data/fit_coeffs.json'

WIDGET_GEOMETRY = {
	'w' : 1600,
	'h' : 800
}

WINDOW_TITLE = 'Electrode Control'

CXN_ID = 110101

class ElectrodeWindow(QtGui.QWidget):
	def __init__(self, reactor, cxn=None):
		super(ElectrodeWindow, self).__init__()
		self.reactor = reactor
		self.cxn = cxn
		self.populate()
                self.resize(WIDGET_GEOMETRY['w'], WIDGET_GEOMETRY['h'])
	
	def populate(self):
		self.setWindowTitle(WINDOW_TITLE)

		self.layout = QtGui.QHBoxLayout()
		self.widget = ElectrodeControl(self.reactor, self, self.cxn)

		self.scroll = QtGui.QScrollArea()
		self.scroll.setWidget(self.widget)
		self.scroll.setWidgetResizable(True)
		self.scroll.setHorizontalScrollBarPolicy(2)
		self.scroll.setVerticalScrollBarPolicy(2)
		self.scroll.setFrameShape(0)

		self.layout.addWidget(self.scroll)
		self.setLayout(self.layout)


class ElectrodeControl(QtGui.QWidget):
	def __init__(self, reactor, parent=None, cxn=None):
		super(ElectrodeControl, self).__init__()
		self.reactor = reactor
		self.cxn = cxn

		self.parent = parent

		self.calculator = ECalculator(fit_coeffs_path)

		self.setFixedWidth(WIDGET_GEOMETRY['w'])
		self.setFixedHeight(WIDGET_GEOMETRY['h'])

		self.populate()
		self.connect_to_labrad()

	def populate(self):
		self.setWindowTitle("Electrode Control")
		self.layout = QtGui.QVBoxLayout()

		self.settings = SettingWidget()
		self.optimizeButton = QtGui.QPushButton('Parameter optimization')
		self.forms = FormWidget(self.calculator)
		self.displays = DisplayWidget(self.calculator)

		self.optimizeButton.clicked.connect(self.optimize)
		self.optimizeButton.setFixedWidth(WIDGET_GEOMETRY['w']/4)

		self.forms.inputForms.crossUpdated.connect(self.inputFormChanged)
		self.settings.updateDescriptionSignal.connect(self.descriptionChanged)

		self.settings.settingChangedSignal.connect(self.settingChanged)
		self.settings.newSettingSignal.connect(self.newSettingAdded)
		self.settings.saveSettingSignal.connect(self.saveSetting)
		self.settings.settingDeletedSignal.connect(self.settingDeleted)
		self.settings.refreshSignal.connect(self.refresh)

		self.layout.addWidget(self.settings)
		self.layout.addWidget(self.optimizeButton)
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
		for p in self.presets:
			if 'volts' not in p:
				p['volts'] = DACsToVs(p['values'])
			p['normalModes'] = VsToNormalModes(p['volts'], p['compShim'])
			p['values'] = VsToDACs(p['volts'])
		self.saveSetting()

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
		self.presets[self.settings.currentSetting]['normalModes'] = VsToNormalModes(vals, comp_shim)
		self.presets[self.settings.currentSetting]['volts'] = vals
		self.presets[self.settings.currentSetting]['values'] = VsToDACs(vals)
		self.presets[self.settings.currentSetting]['compShim'] = comp_shim
		self.displays.setValues(vals, comp_shim)
		self.unsavedChanges()

	def unsavedChanges(self):
		if self.parent:
			self.parent.setWindowTitle(WINDOW_TITLE + '*')
		else:
			self.setWindowTitle(WINDOW_TITLE + '*')

	def savedChanges(self):
		if self.parent:
			self.parent.setWindowTitle(WINDOW_TITLE)
		else:
			self.setWindowTitle(WINDOW_TITLE)

	@inlineCallbacks
	def saveSetting(self):
		yield self.server.update_presets(json.dumps(self.presets))
		self.savedChanges()

	def newSettingAdded(self):
		# Because of aliasing between self.presets and self.settings.presets, following (commented) line is not necessary
		# self.presets.append(self.settings.presets[-1])
		self.settingChanged()

	def settingChanged(self):
		if 'volts' in self.presets[self.settings.currentSetting]:
			vals = self.presets[self.settings.currentSetting]['volts']
			vs = VsToDACs(vals)
		else:
			vs = self.presets[self.settings.currentSetting]['values']
			vals = DACsToVs(vs)
		
		comp_shim = self.presets[self.settings.currentSetting]['compShim']
		self.forms.setValues(vals, comp_shim)
		self.displays.setValues(vals, comp_shim)
		self.savedChanges()

	def settingDeleted(self, index):
		self.presets.pop(index)
		self.unsavedChanges()

	@inlineCallbacks
	def _refresh(self, c, x):
		# The signal is emitted every time the presets are changed or reloaded.
		# We will cause a loop if we refresh every time we catch the signal,
		# since self.refresh() calls self.server.reload_presets(), which 
		# causes the signal to be emitted again.
		# So the signal comes with a bool that tells us if we should update:
		if x:
			yield self.refresh()

	@inlineCallbacks
	def refresh(self):
		yield self.server.reload_presets()
		self.getPresets()


	def optimize(self):
		(vals, comp_shim) = self.forms.getValues()

		dialog = OptimizationDialog(self.calculator, vals, comp_shim)
		if dialog.exec_():
			results = dialog.getResults()
			if results:
				self.forms.setValues(results, comp_shim)

	def closeEvent(self, x):
		self.reactor.stop()



if __name__ == '__main__':
    a = QtGui.QApplication([])
    import qt4reactor 
    qt4reactor.install()
    from twisted.internet import reactor
    widget = ElectrodeWindow(reactor)
    widget.setWindowIcon(QtGui.QIcon('./lib/icon.png'))
    widget.show()
    reactor.run()
