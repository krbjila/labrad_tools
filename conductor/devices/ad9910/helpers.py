import sys
sys.path.append('../')
from generic_device.generic_parameter import GenericParameter

from twisted.internet.defer import inlineCallbacks, Deferred
from twisted.internet.reactor import callLater
from labrad.wrappers import connectAsync

from conductor_device.conductor_parameter import ConductorParameter

import json

class AD9910Device(ConductorParameter):
    """
    Data format:::

        value = {
            'program': [...],
            'profiles': [...],
        }

    See documentation for AD9910Server for the correct format for the ``program`` and ``profile`` lists.
    """
    priority = 1

    def __init__(self, config={}):
        super(AD9910Device, self).__init__(config)
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
            
            if self.device not in devs:
                print('Device {} not found'.format(self.device))

        except AttributeError:
            # Log a warning that the server can't be found.
            # Conductor will throw an error and remove the parameter
            print("ad9910's update: Imaging server not connected.")


    @inlineCallbacks
    def update(self):
        if self.value:
            try:
                program = json.dumps(self.value['program'])
                profiles = json.dumps(self.value['profiles'])

                s = yield self.server.select_device(self.device)
                yield self.server.write_data(program, profiles)
            except Exception as e:
                print(e)