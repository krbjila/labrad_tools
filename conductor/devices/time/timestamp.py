import time

from twisted.internet.defer import inlineCallbacks
from labrad.wrappers import connectAsync

from conductor_device.conductor_parameter import ConductorParameter

class Timestamp(ConductorParameter):
    """
    Timestamp(ConductorParameter)

    Conductor parameter for logging the time when the experiment was run.
    """
    value_type = 'data'
    priority = 2

    @inlineCallbacks
    def update(self):
        yield None
        self._value = time.time()

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        pass


        
