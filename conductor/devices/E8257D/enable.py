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
        self.value = 0
        # ensure that the rf turns on at the beginning of the sequence
        # i.e., ensure that self.state changes at beginning of the sequence
        self.state = -1

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
                        # turn off rf output
                        yield self.cxn.krbjila_gpib.write('OUTP:STAT OFF')
                        # update the state and clear the serial buffer
                        self.state = newstate
                        yield self.trigger.reset_input_buffer()
                            
                        to_run = {}
                        # look for parameters for the triggered state
                        for loc in ['defaults', 'value']:
                            if unicode(self.state) in getattr(self, loc, {}):
                                params = getattr(self, loc)[unicode(self.state)]
                                if u'frequency' in params:
                                    to_run['f'] = params[u'frequency']
                                if u'amplitude' in params:                   
                                    to_run['a'] = params[u'amplitude']
                                if u'evap' in params:
                                    print 'poo'
                                    to_run['e'] = params[u'evap']
                                    print to_run['e']
                        
                        # turn on the output
                        yield self.cxn.krbjila_gpib.write('OUTP:STAT ON')

                        # now, execute the parameters
                        # first, check if an evap trajectory is set up
                        if 'e' in to_run:
                            if to_run['e']:
                                print 'poop'
                                self.evap = evaporation()
                                self.cmds = []
                                for k in range(self.evap.points):
                                    self.cmds.append('FREQ {:0.2f}kHz; VOLT {:0.2f}dbm'.format(self.evap.trajectory[k], self.evap.amps[k]))
                                for k in self.cmds:
                                    self.cxn.krbjila_gpib.write(k)
                                    yield sleep(self.evap.dt)
                        # if not, then just setting a single frequency and/or amplitude
                        elif ('f' in to_run) or ('a' in to_run):
                            if 'f' in to_run:
                               yield self.cxn.krbjila_gpib.write('FREQ ' + str(to_run['f']) + 'MHz')
                            if 'a' in to_run:
                               yield self.cxn.krbjila_gpib.write('POW:AMPL ' + str(to_run['a']) + 'dbm')
                        # if no parameters found, just configure as default
                        else:
                            yield self.cxn.krbjila_gpib.write('FREQ 6834.7MHz')
                            yield self.cxn.krbjila_gpib.write('POW:AMPL -19dbm') 
                            
            # once the while loop has terminated, close the serial connection
            self.trigger.close()
        # if not enabled, output the default (gray molasses)
        else:
            yield self.cxn.krbjila_gpib.write('OUTP:STAT OFF')
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
