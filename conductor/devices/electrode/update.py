import sys, os
sys.path.append(os.path.dirname(os.path.realpath(__file__)))


import json
import requests

from twisted.internet.defer import inlineCallbacks, returnValue
from labrad.wrappers import connectAsync

from conductor_device.conductor_parameter import ConductorParameter
from lib.helpers import *

sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), '../../electrode'))
from electrode.calibrations import ZEROS
from electrode.clients.lib.forms.gui_defaults_helpers import *

class Update(ConductorParameter):
    """
    Update(ConductorParameter)

    Conductor parameter for updating electrode presets when the experiment is run.

    Only supports setting existing presets by normal modes, but normal modes can be calculated from other values using the functions in `gui_defaults_helpers.py <https://github.com/krbjila/labrad_tools/blob/master/electrode/clients/lib/forms/gui_defaults_helpers.py>`_. The field is not updated and an error message is shown if the normal modes are out of range or aren't defined correctly.

    Example config:

    .. code-block:: json

            {
                "80": {
                    "normalModes": {
                        "HGrad": -0.0,
                        "GlobalOffset": -0.0,
                        "RodOffset": 0.0,
                        "Bias": 1012.5,
                        "EastWest": -0.0,
                        "RodScale": 0.4225,
                        "CompShim": 0.0
                    }
                }
            }
    """
    priority = 20
    # value_type = 'list'

    def __init__(self, config={}):
        super(Update, self).__init__(config)
        self.value = self.default

    @inlineCallbacks
    def initialize(self):
        self.cxn = yield connectAsync()
        self.server = yield self.cxn.electrode
        self.zeros = yield self.get_zeros()
        self.url = 'http://127.0.0.1:8000/opt'

    @inlineCallbacks
    def get_zeros(self):
        s = yield self.server.get_presets()
        d = json_loads_byteified(s)
        for x in d:
            if x['id'] == '0':
                returnValue(x)
        returnValue(ZEROS)

    @inlineCallbacks
    def update(self):
        """ value is a dict of presets to update """

        def validate_normal_modes(v):
            for (i,n) in enumerate(FORM_FIELDS['n']):
                min_val = FIELD_MIN['n'][i]
                max_val = FIELD_MAX['n'][i]
                if v['normalModes'][n] < min_val or v['normalModes'][n] > max_val:
                    raise ValueError("Normal mode {}: {} is out of the acceptable range of {} to {}".format(n, v['normalModes'][n], min_val, max_val))

        if self.value:
            for k,v in self.value.items():
                try:
                    if 'optimize' in v:
                        if 'guess' in v['optimize']:
                            # if the guess is an int, it's a preset index
                            if isinstance(v['optimize']['guess'], int):
                                guess = json.loads(self.server.get_presets())[v['optimize']['guess']]['normalModes']
                        # otherwise, the guess is already a normal mode dict
                            elif isinstance(v['optimize']['guess'], dict):
                                guess = v['optimize']['guess']
                        else:
                            guess = json.loads(self.server.get_presets())[k]['normalModes']
                        v["optimize"].update(NormalModesToVs(guess))                                
                        r = requests.post(self.url, json=v['optimize'])
                        if r.status_code == 200:
                            v['volts'] = r.json()['V']
                            v['values'] = VsToDACs(v['volts'])
                            v['normalModes'] = VsToNormalModes(v['volts'])
                            validate_normal_modes(v)
                    elif 'normalModes' in v:
                        validate_normal_modes(v)
                        v['volts'] = NormalModesToVs(v['normalModes'])
                        v['values'] = VsToDACs(v['volts'])
                    else:
                        raise ValueError("Could not determine how to set electrode preset {} to {}".format(k, v))
                except Exception as e:
                    print("Could not set electrode preset {} to {}: {}".format(k, v, e))
            poo = yield self.server.soft_update(json.dumps(self.value))
            print("soft_update for {} complete: result {}".format(k, poo))
