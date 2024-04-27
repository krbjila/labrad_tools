import sys
sys.path.append('../')
from generic_device.generic_parameter import GenericParameter

from twisted.internet.defer import inlineCallbacks, Deferred
from twisted.internet.reactor import callLater
from labrad.wrappers import connectAsync

from conductor_device.conductor_parameter import ConductorParameter

GPIB_ADDRESS = '1'
GPIB_ADDRESS_STR = 'GPIB0::' + GPIB_ADDRESS + '::INSTR'

class Amplitude(ConductorParameter):
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
        super(Amplitude, self).__init__(config)
        self.value = [self.default]

    @inlineCallbacks
    def initialize(self):
        self.cxn = yield connectAsync()
        yield self.cxn.krbjila_gpib.select_interface(GPIB_ADDRESS_STR)

    @inlineCallbacks
    def update(self):
        if self.value:
            # if a single number is given, set the output. Otherwise, set up a sweep.
            if isinstance(self.value, (int, float)):
                a = str(self.value)  # dBm
                yield self.cxn.krbjila_gpib.write(":POW:MODE CW")
                yield self.cxn.krbjila_gpib.write(":POW:AMPL " + a + "dBm")
                yield self.cxn.krbjila_gpib.write(":OUTP ON")
            else:
                powers = [str(f) for f in self.value]
                yield self.cxn.krbjila_gpib.write(":POW:MODE LIST")
                yield self.cxn.krbjila_gpib.write(":LIST:TYPE LIST")
                yield self.cxn.krbjila_gpib.write(":LIST:POW " + ','.join(powers))
                yield self.cxn.krbjila_gpib.write(":LIST:TRIG:SOUR EXT")
                yield self.cxn.krbjila_gpib.write(":TRIG:EXT:DEL 1e-8")
                yield self.cxn.krbjila_gpib.write(":LIST:RETR 0")
                yield self.cxn.krbjila_gpib.write(":LIST:MAN 1")
                yield self.cxn.krbjila_gpib.write(":OUTP ON")