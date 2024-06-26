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

    Conductor parameter for controlling the waveform output by the RF synthesizer.
    """
    priority = 3
    value_type = 'single'

    def __init__(self, config={}):
        super(Waveform, self).__init__(config)
        self.value = self.default_waveform

    @inlineCallbacks
    def initialize(self):
        self.cxn = yield connectAsync()
        self.synthesizer = yield self.cxn.polarkrb_synthesizer

    @inlineCallbacks
    def update(self):
        if self.value and len(self.value) > 0:
            try:
                print("Setting synthesizer waveform...")
                yield self.synthesizer.reset(True)
                yield self.synthesizer.write_timestamps(self.value, True)
                print("Waveform set!")
            except Exception as e:
                print(e)
