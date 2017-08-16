import sys
import numpy as np

from twisted.internet.defer import inlineCallbacks
from labrad.wrappers import connectAsync

sys.path.append('../')
from generic_device.generic_parameter import GenericParameter

class Frequency(GenericParameter):
    priority = 1

    @inlineCallbacks
    def initialize(self):
        self.cxn = yield connectAsync(host='128.138.107.239')
        yield self.cxn.kk.filename(self.filename)
   
    @inlineCallbacks
    def update(self):
        response = yield self.cxn.kk.frequency(self.time_window)
        try:
            self.value = {
                'mean': np.mean(response),
                'std': np.std(response),
            }
        except:
            self.value = {}
