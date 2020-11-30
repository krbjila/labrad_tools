from __future__ import print_function
from labrad.wrappers import connectAsync
import numpy as np
import sys
from twisted.internet.defer import inlineCallbacks

sys.path.append('../')
from generic_device.generic_parameter import GenericParameter

class Voltage(GenericParameter):
    priority = 1
#    value_type = 'once'
    channel_name = None

    @inlineCallbacks
    def initialize(self):
        self.cxn = yield connectAsync()
    
    @inlineCallbacks
    def update(self):
        print(self.channel_name)
        if self.value and self.channel_name:
            for v in np.linspace(4., self.value, 50):
                yield self.cxn.sequencer.channel_manual_output(
                    self.channel_name, v)
            self.value = None
