from twisted.internet.defer import inlineCallbacks
from labrad.wrappers import connectAsync

from conductor_device.conductor_parameter import ConductorParameter

class Frequency(ConductorParameter):
    priority = 1

    @inlineCallbacks
    def initialize(self):
        self.cxn = yield connectAsync()
        yield self.cxn.rf.select_device('clock_steer')
    
    @inlineCallbacks
    def update(self):
        yield self.cxn.rf.frequency(self.value)
