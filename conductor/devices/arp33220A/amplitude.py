import sys
sys.path.append('../')
from generic_device.generic_parameter import GenericParameter

from twisted.internet.defer import inlineCallbacks, Deferred
from twisted.internet.reactor import callLater
from labrad.wrappers import connectAsync

from conductor_device.conductor_parameter import ConductorParameter

class Amplitude(ConductorParameter):
    """
    Amplitude(ConductorParameter)

    Conductor parameter for controlling the frequency of a Keysight/Agilent 33220A AWG's sine output in V. Example config:

    .. code-block:: json

            {
                "arp33220A": {
                    "amplitude": 1
                }
            }
    """
    priority = 1

    def __init__(self, config={}):
        super(Amplitude, self).__init__(config)
        self.value = [self.default_amplitude]

    @inlineCallbacks
    def initialize(self):
        self.cxn = yield connectAsync()
        yield self.cxn.krbjila_gpib.select_interface('GPIB0::22::INSTR')

    @inlineCallbacks
    def update(self):
        if self.value:
            yield self.cxn.krbjila_gpib.write('VOLT ' + str(self.value) +"V")
