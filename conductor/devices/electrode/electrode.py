import sys
import json

from twisted.internet.defer import inlineCallbacks
from labrad.wrappers import connectAsync

from conductor_device.conductor_parameter import ConductorParameter
from lib.helpers import *

LABRAD_FOLDER = '/home/bialkali/labrad_tools/'

sys.path.append(LABRAD_FOLDER + 'electrode/')
from calibrations import ZEROS

sys.path.append(LABRAD_FOLDER + 'electrode/clients/lib/')
from helpers import json_loads_byteified

sys.path.append(LABRAD_FOLDER + 'electrode/clients/lib/forms/')
from gui_defaults_helpers import *

class Electrode(ConductorParameter):
    priority = 20
    value_type = 'list'
    def __init__(self, config={}):
        super(Electrode, self).__init__(config)
        self.value = [self.default_sequence]

    @inlineCallbacks
    def initialize(self):
        self.cxn = yield connectAsync()
        self.server = yield self.cxn.get_server('electrode')
        self.zeros = yield self.get_zeros()

    @inlineCallbacks
    def get_zeros(self):
        s = yield self.server.get_presets()
        d = json_loads_byteified(s)
        for x in d:
            if x['id'] == '0':
                return x['values']
        return ZEROS

    @inlineCallbacks
    def update(self):
        """ value is a dict of presets to update """
        if self.value:
            Vs = deepcopy(self.value)
            for k,v in self.value.items():
                try:
                    Vs[k]['values'] = NormalModesToVs(v['values'])
                except:
                    Vs[k]['values'] = self.zeros
            yield self.server.soft_update(Vs)
