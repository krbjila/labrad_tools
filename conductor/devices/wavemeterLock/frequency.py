import sys
sys.path.append('../')
from generic_device.generic_parameter import GenericParameter

from twisted.internet.defer import inlineCallbacks, Deferred
from twisted.internet.reactor import callLater
from labrad.wrappers import connectAsync

from conductor_device.conductor_parameter import ConductorParameter

class Frequency(ConductorParameter):
    """
    Frequency(ConductorParameter)

    Conductor parameter for controlling the setpoint of a wavemeter lock. The frequency is in THz. Example config:

    .. code-block:: json

            {
                "wavemeterLock": {
                    "frequency": 291.417215
                }
            }
    """
    priority = 3

    def __init__(self, config={}):
        super(Frequency, self).__init__(config)
        self.value = [self.default_frequency]

    @inlineCallbacks
    def initialize(self):
        self.cxn = yield connectAsync()

    @inlineCallbacks
    def update(self):
        if self.value:
            yield self.cxn.wavemeterlaptop_wavemeter.set_setpoint(self.value)
