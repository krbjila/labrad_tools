import sys
sys.path.append('../')
from generic_device.generic_parameter import GenericParameter

from twisted.internet.defer import inlineCallbacks, Deferred
from twisted.internet.reactor import callLater
from labrad.wrappers import connectAsync

from conductor_device.conductor_parameter import ConductorParameter

sys.path.append('/home/bialkali/labrad_tools/magnetic_evaporation')
from evaporate import evaporation

def sleep(secs):
    d = Deferred()
    callLater(secs, d.callback, None)
    return d

class Enable(ConductorParameter):
    priority = 1

    def __init__(self, config={}):
        super(Enable, self).__init__(config)
        self.value = [self.default_gray]

    @inlineCallbacks
    def initialize(self):
        self.cxn = yield connectAsync()
	yield self.cxn.krbjila_gpib.select_interface('GPIB0::19::INSTR')
    
    @inlineCallbacks
    def update(self):
        if self.value:
            yield self.cxn.krbjila_gpib.write('FREQ 6834.7MHz; POW:AMPL -19dbm;')
            yield self.cxn.krbjila_gpib.write('OUTP:STAT ON')
