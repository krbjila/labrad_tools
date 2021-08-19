import sys
sys.path.append('../')
from generic_device.generic_parameter import GenericParameter

from twisted.internet.defer import inlineCallbacks, Deferred
from twisted.internet.reactor import callLater
from labrad.wrappers import connectAsync

from conductor_device.conductor_parameter import ConductorParameter

GPIB_ADDRESS = '1'
GPIB_ADDRESS_STR = 'GPIB0::' + GPIB_ADDRESS + '::INSTR'

class Frequency(ConductorParameter):
    """
    Frequency(ConductorParameter)

    A conductor parameter to set the frequency of the K D1 EOM RF (in MHz). Example config:

    .. code-block:: json

        {
            "kd1": {
                "frequency": 1286
            }
        }
       
    """
    priority = 1

    def __init__(self, config={}):
        super(Frequency, self).__init__(config)
        self.value = [self.default]

    @inlineCallbacks
    def initialize(self):
        self.cxn = yield connectAsync()
	yield self.cxn.krbjila_gpib.select_interface(GPIB_ADDRESS_STR)

    @inlineCallbacks
    def update(self):
        if self.value:
            yield self.cxn.krbjila_gpib.write(":FREQ:CW " + str(self.value) + "MHz")
            yield self.cxn.krbjila_gpib.write(":OUTP ON")
