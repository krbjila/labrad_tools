import sys
import json

from twisted.internet.defer import inlineCallbacks
from labrad.wrappers import connectAsync

from conductor_device.conductor_parameter import ConductorParameter
from lib.helpers import *

class Sequence(ConductorParameter):
    priority = 10
    value_type = 'list'
    def __init__(self, config={}):
        super(Sequence, self).__init__(config)
        self.value = [self.default_sequence]

    @inlineCallbacks
    def initialize(self):
        self.cxn = yield connectAsync()

    @inlineCallbacks
    def update(self):
        """ value can be sequence or list of sub-sequences """
        t_advance = 5
        if self.value:
            parameterized_sequence = value_to_sequence(self)
            parameters = get_parameters(parameterized_sequence)
            parameters_json = json.dumps({'sequencer': parameters})
            pv_json = yield self.cxn.conductor.get_parameter_values(
                    parameters_json, True)
            parameter_values = json.loads(pv_json)['sequencer']
            sequence = substitute_sequence_parameters(parameterized_sequence,
                                                      parameter_values)
            yield self.cxn.sequencer.run_sequence(json.dumps(sequence))
            t_advance = get_duration(sequence)
        yield self.cxn.conductor.advance(t_advance)
