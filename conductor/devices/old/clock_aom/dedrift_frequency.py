from twisted.internet.defer import inlineCallbacks
from labrad.wrappers import connectAsync

from conductor_device.conductor_parameter import ConductorParameter

class DedriftFrequency(ConductorParameter):
    priority = 1
    @inlineCallbacks
    def initialize(self):
        self.cxn = yield connectAsync()
        yield self.cxn.yesr20_gpib.select_interface('GPIB0::23::INSTR')
    
    @inlineCallbacks
    def update(self):
        message = 'MEAS:FREQ? DEF, DEF, (@1)'
        response = yield self.cxn.yesr20_gpib.query(message)
        try:
            self.value = float(response)
        except:
            self.value = None
