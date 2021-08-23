import sys
sys.path.append('../')
from generic_device.generic_parameter import GenericParameter

from twisted.internet.defer import inlineCallbacks, Deferred
from twisted.internet.reactor import callLater
from labrad.wrappers import connectAsync

from conductor_device.conductor_parameter import ConductorParameter
import json

sys.path.append('./devices/sequencer/lib')
from helpers import value_to_sequence, get_parameters, substitute_sequence_parameters


PATH = "../magnetic_evaporation/evap.json"

class valuething(object):
    def __init__(self):
        self.value = ['magEvap']
        self.sequence_directory = "/home/bialkali/data/{}/sequences/"

class Time(ConductorParameter):
    """
    Time(ConductorParameter)

    Conductor parameter to set the ``*MagEvapTime`` parameter.
    """
    priority = 99

    def __init__(self, config={}):
        super(Time, self).__init__(config)
        self.value = [1]

    @inlineCallbacks
    def initialize(self):
        self.cxn = yield connectAsync()

    @inlineCallbacks
    def update(self):
        if self.value:
            with open(PATH, 'r') as f:
                data = json.load(f)
            try:
                param_values = yield self.cxn.conductor.get_parameter_values()
                param_values = json.loads(param_values)['sequencer']
                parameterized_sequence = value_to_sequence(valuething())[0]
                parameters = get_parameters(parameterized_sequence)
                for i in parameters:
                    if i not in param_values:
                        raise Exception("Conductor variables not yet loaded.")
                parameters_json = json.dumps({'sequencer': parameters})
                pv_json = yield self.cxn.conductor.get_parameter_values(
                        parameters_json, True)
                parameter_values = json.loads(pv_json)['sequencer']
                sequence = substitute_sequence_parameters(parameterized_sequence, parameter_values)
                time = 0
                for block in sequence['Trigger@D15'][0:3]:
                    time += block['dt']
            except Exception as e:
                time = 6.7
                print("MagEvapTime Error: could not get MagEvap sequence time; assuming default of %f: %s" % (time, e))
            time = max(data['time'] - time + 0.25, 0.001)
            yield self.cxn.conductor.set_parameter_values(json.dumps({'sequencer': {'*MagEvapTime': time}}))
