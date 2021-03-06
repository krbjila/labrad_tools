import sys
sys.path.append('../')
from generic_device.generic_parameter import GenericParameter

from twisted.internet.defer import inlineCallbacks, Deferred
from twisted.internet.reactor import callLater
from labrad.wrappers import connectAsync

from conductor_device.conductor_parameter import ConductorParameter

class Amplitude(ConductorParameter):
    priority = 1

    def __init__(self, config={}):
        super(Amplitude, self).__init__(config)
        self.value = [self.default_amplitude]

    @inlineCallbacks
    def initialize(self):
        self.cxn = yield connectAsync()
	yield self.cxn.krbjila_gpib.select_interface('GPIB0::22::INSTR')
#        yield self.cxn.krbjila_gpib.write("FUNC RAMP; FUNC:RAMP:SYMM 0;")
#        yield self.cxn.krbjila_gpib.write("BURS:NCYC 1; TRIG:SLOP POS; TRIG:SOUR EXT;")
#        yield self.cxn.krbjila_gpib.write("BURS:STAT ON; OUTP:STAT ON")

    @inlineCallbacks
    def update(self):
        if self.value:
	    yield self.cxn.krbjila_gpib.write('VOLT ' + str(self.value) +"V")
