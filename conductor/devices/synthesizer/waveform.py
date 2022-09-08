import sys
sys.path.append('../')
from generic_device.generic_parameter import GenericParameter

from twisted.internet.defer import inlineCallbacks, Deferred
from twisted.internet.reactor import callLater
from labrad.wrappers import connectAsync

from conductor_device.conductor_parameter import ConductorParameter

class Waveform(ConductorParameter):
    """
    Waveform(ConductorParameter)

    Conductor parameter for controlling the waveform output by the RF synthesizer. Example config:

    .. code-block:: json

            {
                "dg800": {
                    "sin": [{
                        "freq1": 100,
                        "amplitude1": 0.20,
                        "phase1": 0,
                        "offset1": 0,
                        "output1": 1,
                        "gated1": 1,
                        "ncycles1": 5,
                        "freq2": 100,
                        "amplitude2": 0.31,
                        "phase2": 0,
                        "offset2": 0,
                        "output2": 0,
                        "gated2": 1,
                        "ncycles2": 5,
                    }]
                }
            }
    """
    priority = 1

    def __init__(self, config={}):
        super(Waveform, self).__init__(config)
        self.value = [self.default_waveform]

    @inlineCallbacks
    def initialize(self):
        self.cxn = yield connectAsync()
        devices = yield self.cxn.imaging_dg800.get_devices()


    @inlineCallbacks
    def update(self):
        if self.value:
            try:
                pass
            except Exception as e:
                print(e)
