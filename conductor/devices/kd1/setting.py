import sys
sys.path.append('../')
from generic_device.generic_parameter import GenericParameter

from twisted.internet.defer import inlineCallbacks, Deferred
from twisted.internet.reactor import callLater
from labrad.wrappers import connectAsync

from conductor_device.conductor_parameter import ConductorParameter

GPIB_ADDRESS = '1'
GPIB_ADDRESS_STR = 'GPIB0::' + GPIB_ADDRESS + '::INSTR'

class Setting(ConductorParameter):
    """
    Amplitude(ConductorParameter)

    A conductor parameter to set the amplitude of the K D1 EOM RF (in dBm). Example config:

    .. code-block:: json

        {
            "kd1": {
                "amplitude": -11
            }
        }
        
    """
    priority = 3

    def __init__(self, config={}):
        super(Setting, self).__init__(config)
        self.value = [self.default]

    @inlineCallbacks
    def initialize(self):
        self.cxn = yield connectAsync()
        yield self.cxn.krbjila_gpib.select_interface(GPIB_ADDRESS_STR)

    @inlineCallbacks
    def update(self):
        if self.value:
            powers = [str(f) for f in self.value["amplitude"]]
            freqs = [str(f * 1e6) for f in self.value["frequency"]]
            # print("Powers command: :LIST:POW " + ','.join(powers))
            # print("Freqs command: :LIST:FREQ " + ','.join(freqs))
            yield self.cxn.krbjila_gpib.write(":LIST:TYPE LIST")
            yield self.cxn.krbjila_gpib.write(":LIST:FREQ " + ','.join(freqs))
            yield self.cxn.krbjila_gpib.write(":LIST:POW " + ','.join(powers))
            yield self.cxn.krbjila_gpib.write(":LIST:TRIG:SOUR EXT")
            yield self.cxn.krbjila_gpib.write(":LIST:RETR 0")
            yield self.cxn.krbjila_gpib.write(":LIST:MAN 1")
            yield self.cxn.krbjila_gpib.write(":FREQ:MODE LIST")
            yield self.cxn.krbjila_gpib.write(":POW:MODE LIST")
            yield self.cxn.krbjila_gpib.write(":OUTP ON")