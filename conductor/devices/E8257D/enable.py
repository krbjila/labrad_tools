import sys
sys.path.append('../')
from generic_device.generic_parameter import GenericParameter

from twisted.internet.defer import inlineCallbacks, Deferred
from twisted.internet.reactor import callLater
from labrad.wrappers import connectAsync

from conductor_device.conductor_parameter import ConductorParameter

sys.path.append('/home/bialkali/labrad_tools/magnetic_evaporation')
from evaporate import evaporation
import serial
import serial.tools.list_ports

def sleep(secs):
    d = Deferred()
    callLater(secs, d.callback, None)
    return d

class Enable(ConductorParameter):
    priority = 1

    def __init__(self, config={}):
        super(Enable, self).__init__(config)
        self.value = [self.default_enable]

        for k in serial.tools.list_ports.comports():
           try:
               if k.name[0:6] == 'ttyACM':
                   self.port = k.name
           except:
               pass

        try:
            self.port
        except:
            raise Exception('Port does not exist. Reconnect and reload serialSwitch.ino to Arduino.')


    @inlineCallbacks
    def initialize(self):

        self.cxn = yield connectAsync()
	yield self.cxn.krbjila_gpib.select_interface('GPIB0::19::INSTR')
        self.state = 0
    
    @inlineCallbacks
    def update(self):
        # if enabled
        if self.value:
            # connect to serial, set baud rate, and clear the input
            self.trigger = yield serial.Serial('/dev/' + self.port)
            self.trigger.baudrate = 9600
            self.trigger.reset_input_buffer()

            # loop: listen for data from the trigger
            # need to check self.value in order to correctly
            # terminate the while loop when the device is disabled
            while self.value:
                # find the number of bytes in the input buffer
                bytes_waiting = yield self.trigger.in_waiting
                if bytes_waiting:
                    # read the entire buffer
                    newstate = yield int(self.trigger.read(bytes_waiting)[-1])

                    if self.state != newstate:
                        # update state and clear the buffer
                        self.state = newstate
                        yield self.trigger.reset_input_buffer()
                        
                        # if nothing, run default (gray molasses)
                        if self.state == 0:
                            yield self.cxn.krbjila_gpib.write('FREQ 6834.7MHz')
                            yield self.cxn.krbjila_gpib.write('POW:AMPL -19dbm')
                        # if only D08 high, do evaporation
                        if self.state == 1:
                            yield self.cxn.krbjila_gpib.write('FREQ 6834.7MHz')
                            yield self.cxn.krbjila_gpib.write('POW:AMPL -19dbm')
                        # if only D09 high, set up low field ARP
                        if self.state == 2:
                            yield self.cxn.krbjila_gpib.write('FREQ 6898MHz')
                            yield self.cxn.krbjila_gpib.write('POW:AMPL 10dbm')
                        # if only D10 high, set up high field ARP
                        if self.state == 4:
                            yield self.cxn.krbjila_gpib.write('FREQ 8030MHz')
                            yield self.cxn.krbjila_gpib.write('POW:AMPL 10dbm')
            # once the while loop has terminated, close the serial connection
            self.trigger.close()
        # if not enabled, output the default (gray molasses)
        else:
            yield self.cxn.krbjila_gpib.write('FREQ 6834.7MHz')
            yield self.cxn.krbjila_gpib.write('POW:AMPL -19dbm')

#	    self.evap = evaporation()
#            self.cmds = []
#	    for k in range(self.evap.points):
#	        self.cmds.append('FREQ {:0.2f}kHz; VOLT {:0.2f}dbm'.format(self.evap.trajectory[k],self.evap.amps[k]))
#            
#            yield sleep(self.value) # Wait time until the start of evap
#
#            yield self.cxn.krbjila_gpib.write('OUTP:STAT ON')
#            for k in self.cmds:
#                self.cxn.krbjila_gpib.write(k)
#                yield sleep(self.evap.dt)
#            yield self.cxn.krbjila_gpib.write('OUTP:STAT OFF')
