import sys, os
sys.path.append(os.path.dirname(os.path.realpath(__file__)))

import json

from twisted.internet.defer import inlineCallbacks, returnValue
from labrad.wrappers import connectAsync
from time import sleep

from conductor_device.conductor_parameter import ConductorParameter
from lib.helpers import *

class Sequence(ConductorParameter):
    """
    Sequence(ConductorParameter)

    Conductor parameter for setting the sequence

    TODO: Finish documenting this.
    """
    priority = 2
    value_type = 'list'
    critical = True
    
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
            # Have to do a bit of work here to get the electrode sequence
            (parameterized_sequence, electrode_sequence) = yield value_to_sequence(self, self.cxn)
            (ret, electrode_presets, e_channels) = yield self.get_e()

            # Only update the parameters if get_e() returned successful
            # Otherwise we will just leave the values that are written in
            if ret == 0:
                parameterized_sequence = update_electrode_values(parameterized_sequence, electrode_sequence, electrode_presets, e_channels)
            # This part unchanged from before:
            parameters = get_parameters(parameterized_sequence)
            parameters_json = json.dumps({'sequencer': parameters})
            pv_json = yield self.cxn.conductor.get_parameter_values(
                    parameters_json, True)
            parameter_values = json.loads(pv_json)['sequencer']
            sequence = substitute_sequence_parameters(parameterized_sequence,
                                                      parameter_values)
            # fname = "/home/bialkali/labrad_tools/conductor/devices/sequencer/sequences/sequence_{}.json".format(datetime.now().strftime("%d-%m-%y_%H-%M-%S"))
            # with open(fname, "w+") as f:
            #     json.dump(sequence, f)
            # sleep(5)
            yield self.cxn.sequencer.run_sequence(json.dumps(sequence))
            t_advance = get_duration(sequence)
            # yield self.cxn.conductor.advance_logging()
        yield self.cxn.conductor.advance(t_advance)

    @inlineCallbacks
    def get_e(self):
       try:
           electrode_presets = yield self.cxn.electrode.get_presets()
           electrode_presets = fix_electrode_presets(json.loads(electrode_presets))

           e_channels = yield self.cxn.electrode.get_channels()
           e_channels = json.loads(e_channels)

           all_channels = yield self.cxn.sequencer.get_channels()
           all_channels = json.loads(all_channels)
           e_channels = get_electrode_nameloc(e_channels, all_channels)

           returnValue((0, electrode_presets, e_channels))
       except Exception as e:
           print(e)
           returnValue((-1, {}, {}))
