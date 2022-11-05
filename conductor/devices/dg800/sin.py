import sys
sys.path.append('../')
from generic_device.generic_parameter import GenericParameter

from twisted.internet.defer import inlineCallbacks, Deferred
from twisted.internet.reactor import callLater
from labrad.wrappers import connectAsync

from conductor_device.conductor_parameter import ConductorParameter

class Sin(ConductorParameter):
    """
    Sin(ConductorParameter)

    Conductor parameter for controlling the frequency, amplitude (Vpp), offset (V), phase (deg), and enable and gating status of each of the Rigol DG800's channels. Example config:

    .. code-block:: json

            {
                "dg800": {
                    "sin": [{
                        "freq1": 100,
                        "amplitude1": 0.20,
                        "phase1": 0,
                        "offset1": 0,
                        "output1": 1,
                        "gated1": 1,
                        "ncycles1": 5,
                        "freq2": 100,
                        "amplitude2": 0.31,
                        "phase2": 0,
                        "offset2": 0,
                        "output2": 0,
                        "gated2": 1,
                        "ncycles2": 5,
                    }]
                }
            }
    """
    priority = 1

    def __init__(self, config={}):
        super(Sin, self).__init__(config)
        self.value = [self.default_sin]

    @inlineCallbacks
    def initialize(self):
        self.cxn = yield connectAsync()
        devices = yield self.cxn.imaging_dg800.get_devices()
        try:
            yield self.cxn.imaging_dg800.select_device(devices[0])
            yield self.cxn.imaging_dg800.set_impedance(1, 50)
            yield self.cxn.imaging_dg800.set_impedance(2, 50)

            yield self.cxn.imaging_dg800.set_sin(1,
                self.value['freq1'], self.value['amplitude1'], self.value['offset1'], self.value['phase1'])
            yield self.cxn.imaging_dg800.set_sin(2,
                self.value['freq2'], self.value['amplitude2'], self.value['offset2'], self.value['phase2'])
            yield self.cxn.imaging_dg800.set_output(1,bool(self.value['output1']))
            yield self.cxn.imaging_dg800.set_output(2,bool(self.value['output2']))
            # yield self.cxn.imaging_dg800.set_ncycles(1,int(self.value['ncycles1']))
            # yield self.cxn.imaging_dg800.set_ncycles(2,int(self.value['ncycles2']))
            # yield self.cxn.imaging_dg800.set_gated(1,bool(self.value['gated1']))
            # yield self.cxn.imaging_dg800.set_gated(2,bool(self.value['gated2']))
        except Exception as e:
            print(e)

    @inlineCallbacks
    def update(self):
        if self.value:
            try:
                yield self.cxn.imaging_dg800.set_sin(1,
                    self.value['freq1'], self.value['amplitude1'], self.value['offset1'], self.value['phase1'])
                yield self.cxn.imaging_dg800.set_sin(2,
                    self.value['freq2'], self.value['amplitude2'], self.value['offset2'], self.value['phase2'])
                yield self.cxn.imaging_dg800.set_output(1,bool(self.value['output1']))
                yield self.cxn.imaging_dg800.set_output(2,bool(self.value['output2']))
                # yield self.cxn.imaging_dg800.set_ncycles(1,int(self.value['ncycles1']))
                # yield self.cxn.imaging_dg800.set_ncycles(2,int(self.value['ncycles2']))
                # yield self.cxn.imaging_dg800.set_gated(1,bool(self.value['gated1']))
                # yield self.cxn.imaging_dg800.set_gated(2,bool(self.value['gated2']))
            except Exception as e:
                print(e)
