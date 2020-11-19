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
        self.state = 0
        self.ID_case = 8008
        self.ID_start = 8009
        self.ID_stop = 8010
        self.ID_update = 8011
        self.to_run = {}

    @inlineCallbacks
    def initialize(self):

        self.cxn = yield connectAsync()
        yield self.cxn.krbjila_gpib.select_interface('GPIB0::19::INSTR')

        yield self.cxn.krbjila_arduino.signal__case(self.ID_case)
        yield self.cxn.krbjila_arduino.addListener(listener = self.advanceAction, source = None, ID = self.ID_case)

        yield self.cxn.conductor.signal__parameters_updated(self.ID_update)
        yield self.cxn.conductor.addListener(listener = self.updateAction, source = None, ID = self.ID_update)

        yield self.cxn.conductor.signal__experiment_started(self.ID_start)
        yield self.cxn.conductor.addListener(listener = self.startAction, source = None, ID = self.ID_start)

        yield self.cxn.conductor.signal__experiment_stopped(self.ID_stop)
        yield self.cxn.conductor.addListener(listener = self.stopAction, source = None, ID = self.ID_stop)

    @inlineCallbacks
    def startAction(self, cntx, signal):
        # turn off the output before proceeding
        yield self.cxn.krbjila_gpib.write('OUTP:STAT OFF')
        yield self.cxn.krbjila_gpib.write('FM1:STAT OFF')
        # if enabled and the signal is True
        if self.default_enable and signal:
            # look for defaults set in config file
            if self.defaults[u'0']:
                defaults = self.defaults[u'0']
                if u'frequency' in defaults:
                    f = str(defaults[u'frequency'])
                    yield self.cxn.krbjila_gpib.write('FREQ ' + f + 'MHz')
                if u'amplitude' in defaults:
                    a = str(defaults[u'amplitude'])
                    yield self.cxn.krbjila_gpib.write('POW:AMPL ' + a + 'dbm')
                yield self.cxn.krbjila_gpib.write('OUTP:STAT ON')
            # otherwise output default parameters
            else:
                yield self.cxn.krbjila_gpib.write('FREQ 6834.7MHz')
                yield self.cxn.krbjila_gpib.write('POW:AMPL -19dbm')
                yield self.cxn.krbjila_gpib.write('OUTP:STAT ON')

    @inlineCallbacks
    def stopAction(self, cntx, signal):
        if signal:
            yield self.cxn.krbjila_gpib.write('OUTP:STAT OFF')
            yield self.cxn.krbjila_gpib.write('FM1:STAT OFF')
            if self.defaults[u'0']:
                defaults = self.defaults[u'0']
                if u'frequency' in defaults:
                    f = str(defaults[u'frequency'])
                    yield self.cxn.krbjila_gpib.write('FREQ ' + f + 'MHz')
                if u'amplitude' in defaults:
                    a = str(defaults[u'amplitude'])
                    yield self.cxn.krbjila_gpib.write('POW:AMPL ' + a + 'dbm')

    @inlineCallbacks
    def advanceAction(self, cntx, signal):
        if self.value:
            yield self.cxn.krbjila_gpib.write('OUTP:STAT OFF')
            state = signal
            self.state = state
            if str(state) in self.to_run:
                to_run = self.to_run[str(state)]
                if 'e' in to_run:
                    if to_run['e']:
                        self.evap = evaporation()
                        self.cmds = []
                        for k in range(self.evap.points):
                            self.cmds.append('FREQ {:0.2f}MHz; POW:AMPL {:0.2f}dbm'.format(self.evap.trajectory[k], self.evap.amps[k]))
    
                        yield self.cxn.krbjila_gpib.write('OUTP:STAT ON')
                        for k in self.cmds:
                            self.cxn.krbjila_gpib.write(k)
                            yield sleep(self.evap.dt)
                # if not, then just setting a single frequency and/or amplitude
                elif ('f' in to_run) or ('a' in to_run) or ('d' in to_run):
                    if 'f' in to_run:
                       yield self.cxn.krbjila_gpib.write('FREQ ' + str(to_run['f']) + 'MHz')
                    if 'a' in to_run:
                       yield self.cxn.krbjila_gpib.write('POW:AMPL ' + str(to_run['a']) + 'dbm')
                    if 'd' in to_run:
                       if 's' in to_run:
                           if to_run['s'] == 2:
                               yield self.cxn.krbjila_gpib.write('FM1:SOUR EXT2')
                           else:
                               yield self.cxn.krbjila_gpib.write('FM1:SOUR EXT1')
                       else:
                           yield self.cxn.krbjila_gpib.write('FM1:SOUR EXT1')
                       yield self.cxn.krbjila_gpib.write('FM1:DEV ' + str(to_run['d']) + 'MHz')
                       yield self.cxn.krbjila_gpib.write('FM1:STAT ON')
                       yield self.cxn.krbjila_gpib.write('OUTP:MOD ON')
                    yield self.cxn.krbjila_gpib.write('OUTP:STAT ON')  
            else:
                yield self.cxn.krbjila_gpib.write('FREQ 6834.7MHz')
                yield self.cxn.krbjila_gpib.write('POW:AMPL -19dbm') 

    @inlineCallbacks
    def updateAction(self, cntx, signal):
        if self.value:
            yield self.cxn.krbjila_gpib.write('OUTP:STAT OFF')
            state = self.state
            if str(state) in self.to_run:
                to_run = self.to_run[str(state)]
                if 'e' in to_run:
                    if to_run['e']:
                        self.evap = evaporation()
                        self.cmds = []
                        for k in range(self.evap.points):
                            self.cmds.append('FREQ {:0.2f}MHz; POW:AMPL {:0.2f}dbm'.format(self.evap.trajectory[k], self.evap.amps[k]))
    
                        yield self.cxn.krbjila_gpib.write('OUTP:STAT ON')
                        for k in self.cmds:
                            self.cxn.krbjila_gpib.write(k)
                            yield sleep(self.evap.dt)
                # if not, then just setting a single frequency and/or amplitude
                elif ('f' in to_run) or ('a' in to_run) or ('d' in to_run):
                    if 'f' in to_run:
                       yield self.cxn.krbjila_gpib.write('FREQ ' + str(to_run['f']) + 'MHz')
                    if 'a' in to_run:
                       yield self.cxn.krbjila_gpib.write('POW:AMPL ' + str(to_run['a']) + 'dbm')
                    if 'd' in to_run:
                       if 's' in to_run:
                           if to_run['s'] == 2:
                               yield self.cxn.krbjila_gpib.write('FM1:SOUR EXT2')
                           else:
                               yield self.cxn.krbjila_gpib.write('FM1:SOUR EXT1')
                       else:
                           yield self.cxn.krbjila_gpib.write('FM1:SOUR EXT1')
                       yield self.cxn.krbjila_gpib.write('FM1:DEV ' + str(to_run['d']) + 'MHz')
                       yield self.cxn.krbjila_gpib.write('FM1:STAT ON')
                       yield self.cxn.krbjila_gpib.write('OUTP:MOD ON')
                    yield self.cxn.krbjila_gpib.write('OUTP:STAT ON')  
            else:
                yield self.cxn.krbjila_gpib.write('FREQ 6834.7MHz')
                yield self.cxn.krbjila_gpib.write('POW:AMPL -19dbm') 

    def update(self):
        self.to_run = {}
        # look for parameters for the triggered state
        for attr in ['defaults', 'value']:
            loc = getattr(self, attr, {})
            
            # this check is very important! otherwise everything will break when
            # the defaults are run at the end of the experiment
            if type(loc) is not int:
                for state in range(8):
                    if unicode(state) in loc:
                        params = loc[unicode(state)]
                        state = str(state)
                        self.to_run[state] = {}
                        if u'frequency' in params:
                            self.to_run[state]['f'] = params[u'frequency']
                        if u'amplitude' in params:                   
                            self.to_run[state]['a'] = params[u'amplitude']
                        if u'evap' in params:
                            self.to_run[state]['e'] = params[u'evap']
                        if u'dev' in params:
                            self.to_run[state]['d'] = params[u'dev']
                        if u'source' in params:
                            self.to_run[state]['s'] = params[u'source']
