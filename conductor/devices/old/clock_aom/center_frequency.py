from twisted.internet.defer import inlineCallbacks
from labrad.wrappers import connectAsync

from conductor_device.conductor_parameter import ConductorParameter

class CenterFrequency(ConductorParameter):
    priority = 1
    @inlineCallbacks
    def initialize(self):
        self.cxn = yield connectAsync()
        yield self.cxn.rf.select_device('clock_center')
    
    @inlineCallbacks
    def update(self):
        yield self.cxn.rf.frequency(self.value)
