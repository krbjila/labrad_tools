import sys
sys.path.append('../')
from generic_device.generic_parameter import GenericParameter

from twisted.internet.defer import inlineCallbacks, Deferred
from twisted.internet.reactor import callLater
from labrad.wrappers import connectAsync

from conductor_device.conductor_parameter import ConductorParameter

import serial
import json

arduino_address = 'COM4'

DEVICES = ['N=1', 'N=2']

class Update(ConductorParameter):
    """
    Data format:::

        value = {
            'N=1': {
                'program': [...],
                'profiles': [...],
            },
            'N=2': {
                'program': [...],
                'profiles': [...],
            }
        }

    See documentation for AD9910Server for the correct format for the ``program`` and ``profile`` lists.
    """
    priority = 1

    def __init__(self, config={}):
        super(Update, self).__init__(config)
        try:
            self.value = self.default
        except AttributeError:
            # a default was never loaded
            # this can happen if the parameter was called
            # with invalid arguments. just set it to 0
            self.value = 0
            self.default = 0

    @inlineCallbacks
    def initialize(self):
        self.cxn = yield connectAsync()
        try:
            self.server = self.cxn.imaging_ad9910
            devs = yield self.server.get_device_list()
            
            for d in DEVICES:
                if d not in devs:
                    print('Device {} not found'.format(d))

        except AttributeError:
            # Log a warning that the server can't be found.
            # Conductor will throw an error and remove the parameter
            print("ad9910's update: Imaging server not connected.")


    @inlineCallbacks
    def update(self):
        if self.value:
            for d in DEVICES:
                try:
                    data = self.value[d]
                    program = data['program']

                    # Handle a corner case: if the last line in the program is a sweep,
                    # the profiles don't work correctly. So ensure that the last line in the program
                    # is not a sweep:
                    last = program[-1]
                    if last['mode'] == 'sweep':
                        program.append({u'mode': u'single', u'freq': 0, u'ampl': 0, u'phase': 0})

                    program = json.dumps(program)
                    profiles = json.dumps(data['profiles'])

                    yield self.server.select_device(d)
                    yield self.server.write_data(program, profiles)
                except Exception as e:
                    print(e)

