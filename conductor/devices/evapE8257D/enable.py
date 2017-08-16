import sys
sys.path.append('../')
from generic_device.generic_parameter import GenericParameter

from twisted.internet.defer import inlineCallbacks, Deferred
from twisted.internet.reactor import callLater
from labrad.wrappers import connectAsync

from conductor_device.conductor_parameter import ConductorParameter

sys.path.append('/home/bialkali/labrad_tools/magnetic_evaporation')
from evaporate import evaporation

def sleep(secs):
    d = Deferred()
    callLater(secs, d.callback, None)
    return d

class Enable(ConductorParameter):
    priority = 1

    def __init__(self, config={}):
        super(Enable, self).__init__(config)
        self.value = 0

    @inlineCallbacks
    def initialize(self):
        self.cxn = yield connectAsync()
	yield self.cxn.krbjila_gpib.select_interface('GPIB0::19::INSTR')
    
    @inlineCallbacks
    def update(self):
        if self.value:
	    self.evap = evaporation()
            self.cmds = []
	    for k in range(self.evap.points):
	        self.cmds.append('FREQ {:0.2f}kHz; VOLT {:0.2f}dbm'.format(self.evap.trajectory[k],self.evap.amps[k]))
            
            yield sleep(self.value) # Wait time until the start of evap

            yield self.cxn.krbjila_gpib.write('OUTP:STAT ON')
            for k in self.cmds:
                self.cxn.krbjila_gpib.write(k)
                yield sleep(self.evap.dt)
            yield self.cxn.krbjila_gpib.write('OUTP:STAT OFF')
