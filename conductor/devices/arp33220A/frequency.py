import sys
sys.path.append('../')
from generic_device.generic_parameter import GenericParameter

from twisted.internet.defer import inlineCallbacks, Deferred
from twisted.internet.reactor import callLater
from labrad.wrappers import connectAsync

from conductor_device.conductor_parameter import ConductorParameter

class Frequency(ConductorParameter):
    priority = 1

    def __init__(self, config={}):
        super(Frequency, self).__init__(config)
        self.value = [self.default_frequency]

    @inlineCallbacks
    def initialize(self):
        self.cxn = yield connectAsync()
	yield self.cxn.krbjila_gpib.select_interface('GPIB0::22::INSTR')
        yield self.cxn.krbjila_gpib.write("FUNC SIN")
#        yield self.cxn.krbjila_gpib.write("FUNC RAMP")
#        yield self.cxn.krbjila_gpib.write("FUNC:RAMP:SYMM 0")
#        yield self.cxn.krbjila_gpib.write("BURS:NCYC 1")
#        yield self.cxn.krbjila_gpib.write("TRIG:SLOP POS")
#        yield self.cxn.krbjila_gpib.write("TRIG:SOUR EXT")
#        yield self.cxn.krbjila_gpib.write('BURS:STAT ON')
        yield self.cxn.krbjila_gpib.write('OUTP:STAT ON')
#        yield self.cxn.krbjila_gpib.write('OUTP ON')

    @inlineCallbacks
    def update(self):
        if self.value:
	    yield self.cxn.krbjila_gpib.write('FREQ ' + str(self.value) +"kHz")
