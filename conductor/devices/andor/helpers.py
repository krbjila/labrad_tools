import sys

from twisted.internet.defer import inlineCallbacks
from labrad.wrappers import connectAsync

from conductor_device.conductor_parameter import ConductorParameter

from traceback import print_exc

class AndorDevice(ConductorParameter):
    """
    Conductor parameter for controlling Andor cameras. Individual cameras should subclass this. The configuration for which hardware a conductor parameter communicates with is set in :mod:`conductor.conductor`'s `config.json <https://github.com/krbjila/labrad_tools/blob/master/conductor/config.json>`_.
    Data format:::
        [...]
    """
    priority = 1
    value_type = 'list'

    def __init__(self, server_name, serial, config={}):
        super(AndorDevice, self).__init__(config)
        self.serial = serial
        self.server_name = server_name
        self.value = None

    @inlineCallbacks
    def initialize(self):
        self.cxn = yield connectAsync()
        self.server = self.cxn[self.server_name]


    @inlineCallbacks
    def update(self):
        if self.value:
            try:
                # TODO: set camera parameters and acquire image
                pass
            except Exception as e:
                print_exc(e)