from twisted.internet.defer import inlineCallbacks
from labrad.wrappers import connectAsync

from conductor_device.conductor_parameter import ConductorParameter

class Position(ConductorParameter):
    priority = 1
    def __init__(self, config):
        super(Position, self).__init__(config)
        self.value = 2200

    @inlineCallbacks
    def initialize(self):
        self.cxn = yield connectAsync()
        yield self.cxn.stepper_motor.select_device('nd_filter')
    
    @inlineCallbacks
    def update(self):
        yield self.cxn.stepper_motor.move_absolute(self.value)
