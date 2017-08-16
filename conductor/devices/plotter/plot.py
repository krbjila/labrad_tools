import json

from labrad.wrappers import connectAsync
from twisted.internet.defer import inlineCallbacks

from matplotlib import pyplot as plt

from conductor_device.conductor_parameter import ConductorParameter

class Plot(ConductorParameter):
    priority = 1

    @inlineCallbacks
    def initialize(self):
        self.cxn = yield connectAsync()
    
    @inlineCallbacks
    def update(self):
        if self.value:
            yield self.cxn.plotter.plot(json.dumps(self.value))
