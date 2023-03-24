import sys
sys.path.append('../')

LABRAD_FOLDER = '/home/bialkali/labrad_tools/'
sys.path.append(LABRAD_FOLDER + 'synthesizer/')

from generic_device.generic_parameter import GenericParameter

from twisted.internet.defer import inlineCallbacks, Deferred
from twisted.internet.reactor import callLater
from labrad.wrappers import connectAsync

from conductor_device.conductor_parameter import ConductorParameter

# import synthesizer_sequences as ss
import pickle, json

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
            #     seq, durations = ss.compile_sequence(pickle.loads(self.value))
                yield self.synthesizer.reset()
            #     for i, channel in enumerate(seq):
            #         yield self.synthesizer.write_timestamps(channel, i)
            #     # Set *RF1, *RF2, *RF3, *RF4 to the durations of the first four blocks of the first channel
            #     for i in range(1, min(4, len(durations[0]))):
            #         if durations[0][i] > 0:
            #             yield self.cxn.conductor.set_parameter_values(json.dumps({'sequencer': {'*RF{}'.format(i+1): durations[0][i]}}))
            except Exception as e:
                print(e)
