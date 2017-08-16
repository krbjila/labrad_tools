import json
from twisted.internet.defer import inlineCallbacks
from labrad.wrappers import connectAsync

from devices.conductor_device.conductor_parameter import ConductorParameter
from lib.pid import Dither, DitherPIID

class DitherLock(ConductorParameter):
    priority = 9
#    value_type = 'list'
    def __init__(self, config):
        super(DitherLock, self).__init__(config)
        self.pid = {lock_name: DitherPIID(**lock_conf['pid']) 
            for lock_name, lock_conf in config.items()}
        self.dither = {lock_name: Dither(**lock_conf['dither']) 
            for lock_name, lock_conf in config.items()}
        self._value = {}

    @inlineCallbacks
    def initialize(self):
        self.cxn = yield connectAsync()

    @inlineCallbacks
    def update(self):
        """ sefl.value == {
            'dither': [dither_name, side],
            'pid': [pid_name, side],
        }
        """
#        print 'update: ', self._value
        dither_value = self.value.get('dither')
        if dither_value:
            name = dither_value[0]
            side = dither_value[1]
            center = self.pid[name].output
            out = self.dither[name].tick(side, center)
            clock_aom_value = {'clock_aom': {'frequency': out}}
            yield self.cxn.conductor.set_parameter_values(json.dumps(clock_aom_value))

        pid_value = self.value.get('pid')
        if pid_value:
            data = yield self.cxn.conductor.get_data().addCallback(json.loads)
            if data:
                name = pid_value[0]
                side = pid_value[1]
                frac = data['gage']['frac'][-1]
                out = self.pid[name].tick(side, frac)
                pid_value = {name: {'frequency': out}}
#                print 'lock: ', side, frac, out
                yield self.cxn.conductor.set_parameter_values(json.dumps(pid_value), True)
