import sys
sys.path.append('../')
from generic_device.generic_parameter import GenericParameter

from twisted.internet.defer import inlineCallbacks, Deferred
from twisted.internet.reactor import callLater
from labrad.wrappers import connectAsync

from conductor_device.conductor_parameter import ConductorParameter

import synthesizer.synthesizer_sequences as ss

class Waveform(ConductorParameter):
    """
    Waveform(ConductorParameter)

    Conductor parameter for controlling the waveform output by the RF synthesizer.
    """
    priority = 1
    value_type = 'list'

    def __init__(self, config={}):
        super(Waveform, self).__init__(config)
        self.value = [self.default_waveform]

    @inlineCallbacks
    def initialize(self):
        self.cxn = yield connectAsync()
        self.synthesizer = yield self.cxn.synthesizer

    @inlineCallbacks
    def update(self):
        if self.value:
            try:
                seq = ss.compile_sequence(self.value)
                yield self.synthesizer.reset()
                for i, channel in enumerate(seq):
                    yield self.synthesizer.write_timestamps(channel, i)
            except Exception as e:
                print(e)
