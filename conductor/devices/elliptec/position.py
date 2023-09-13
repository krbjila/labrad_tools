import sys
sys.path.append('../')
from generic_device.generic_parameter import GenericParameter

from twisted.internet.defer import inlineCallbacks, Deferred
from twisted.internet.reactor import callLater
from labrad.wrappers import connectAsync

from conductor_device.conductor_parameter import ConductorParameter

from time import sleep

class Position(ConductorParameter):
    """
    Position(ConductorParameter)

    Conductor parameter for setting the position (in mm) of a Thorlabs Elliptec stage.

    Not currently used in the experiment. Example config:

    .. code-block:: json

        {
            "elliptec": {
                "position": 5.0
            }
        }

    """
    priority = 3

    def __init__(self, config={}):
        super(Position, self).__init__(config)
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
            self.server = self.cxn.imaging_elliptec
            interfaces = yield self.server.get_interface_list()
            interface = interfaces[0]
            yield self.server.select_interface(interface)
            # yield self.server.home()
            # sleep(2)
            # yield self.server.move_abs(self.default)
        except Exception as e:
            # Log a warning that the server can't be found.
            # Conductor will throw an error and remove the parameter
            print("Could not connect to elliptec stage: {}".format(e))


    @inlineCallbacks
    def update(self):
        if self.value:
            try:
                yield self.server.move_abs(self.value)
            except Exception as e:
                print("Could not move elliptec stage to position {}: {}".format(self.value, e))

