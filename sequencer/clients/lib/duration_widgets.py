import sys

from PyQt4 import QtGui

from pathlib import Path
sys.path.append([str(i) for i in Path(__file__).parents if str(i).endswith("labrad_tools")][0])
from client_tools.widgets import SuperSpinBox

class DurationRow(QtGui.QWidget):
    """ row of boxes for sequence timing """
    def __init__(self, config):
        super(DurationRow, self).__init__(None)
        self.config = config
        self.populate()

    def populate(self):
        units =  [(0, 's'), (-3, 'ms'), (-6, 'us'), (-9, 'ns')]
        self.boxes = [SuperSpinBox([500e-9, 60], units) for i in range(self.config.max_columns)]
        self.layout = QtGui.QHBoxLayout()
        for db in self.boxes:
            self.layout.addWidget(db)
        self.setLayout(self.layout)
        self.layout.setSpacing(0)
        self.layout.setContentsMargins(0, 0, 0, 0)

#    def setSequence(self, sequence):
#        self.sequence = sequence
    
    def displaySequence(self, sequence):
        shown = sum([1 for b in self.boxes if not b.isHidden()])
        num_to_show = len(sequence[self.config.timing_channel])
        if shown > num_to_show:
            for b in self.boxes[num_to_show:shown][::-1]:
                b.hide()
        elif shown < num_to_show:
            for b in self.boxes[shown:num_to_show]:
                b.show()
        for b, s in zip(self.boxes[:num_to_show], sequence[self.config.timing_channel]):
            b.display(s['dt'])

    def updateParameters(self, sequence_parameters):
        pass
    


