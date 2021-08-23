import sys
sys.path.append('../')
from conductor_device.conductor_parameter import ConductorParameter

from twisted.internet.defer import inlineCallbacks, Deferred
from labrad.wrappers import connectAsync

class Duration(ConductorParameter):
    priority = 1

    def __init__(self, config={}):
        super(Duration, self).__init__(config)
        self.value = [self.default]

    @inlineCallbacks
    def initialize(self):
        self.cxn = yield connectAsync()
        self.server = self.cxn.krbjila_gpib
        yield self.server.select_interface('GPIB0::10::INSTR')
        yield self.server.write("FUNC RAMP")
        yield self.server.write("FUNC:RAMP:SYMM 0")
        yield self.server.write("BURS:NCYC 1")
        yield self.server.write("TRIG:SLOP POS")
        yield self.server.write("TRIG:SOUR EXT")
        yield self.server.write('BURS:STAT ON')
        yield self.server.write('VOLT 2V')
        yield self.server.write('VOLT:OFFS 0V')
        yield self.server.write('OUTP:STAT ON')

    @inlineCallbacks
    def update(self):
        if self.value:
            f = 1.0/self.value
	    yield self.server.write('FREQ ' + str(f) +"kHz")
