import sys
sys.path.append('../')

LABRAD_FOLDER = '/home/bialkali/labrad_tools/'
sys.path.append(LABRAD_FOLDER + 'synthesizer/')

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
    priority = 99
    value_type = 'list'

    def __init__(self, config={}):
        super(Waveform, self).__init__(config)
        self.value = [self.default_waveform]

    @inlineCallbacks
    def initialize(self):
        self.cxn = yield connectAsync()
        self.synthesizer = yield self.cxn.krbg2_synthesizer

    @inlineCallbacks
    def update(self):
        if self.value:
            print("AAAAAAAA SYNTH UPDATED!!!! {}".format(self.value))
            try:
                yield self.synthesizer.reset()
                yield self.synthesizer.write_timestamps(self.value, True, False)
            except Exception as e:
                print(e)
