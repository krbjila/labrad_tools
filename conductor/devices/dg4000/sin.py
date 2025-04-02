import sys
import numpy as np
from time import sleep

sys.path.append("../")
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
                "dg4000": {
                    "sin": [{
                        "freq2": 100,
                        "amplitude2": 0.31,
                        "phase2": 0,
                        "offset2": 0,
                        "output2": 0,
                    }]
                }
            }
    """

    priority = 3

    def __init__(self, config={}):
        super(Sin, self).__init__(config)
        self.value = [self.default_sin]

    @inlineCallbacks
    def initialize(self):
        self.cxn = yield connectAsync()
        devices = yield self.cxn.polarkrb_dg4000.get_devices()
        self.value = None
        try:
            yield self.cxn.polarkrb_dg4000.select_device(devices[0])
            # yield self.cxn.polarkrb_dg4000.set_impedance(1, 50)
            # yield self.cxn.polarkrb_dg4000.set_impedance(2, 50)

            # # yield self.cxn.polarkrb_dg4000.set_sin(
            # #     1,
            # #     self.value["freq1"],
            # #     self.value["amplitude1"],
            # #     self.value["offset1"],
            # #     self.value["phase1"],
            # # )
            # yield self.cxn.polarkrb_dg4000.set_sin(
            #     2,
            #     self.value["freq2"],
            #     self.value["amplitude2"],
            #     self.value["offset2"],
            #     self.value["phase2"],
            # )
            # # yield self.cxn.polarkrb_dg4000.set_output(1, bool(self.value["output1"]))
            # yield self.cxn.polarkrb_dg4000.set_output(2, bool(self.value["output2"]))
            # # yield self.cxn.polarkrb_dg4000.set_ncycles(1,int(self.value['ncycles1']))
            # # yield self.cxn.polarkrb_dg4000.set_ncycles(2,int(self.value['ncycles2']))
            # # yield self.cxn.polarkrb_dg4000.set_gated(1,bool(self.value['gated1']))
            # # yield self.cxn.polarkrb_dg4000.set_gated(2,bool(self.value['gated2']))
        except Exception as e:
            print(e)

    @inlineCallbacks
    def update(self):
        if self.value:
            try:
                keys = ["freq1", "amplitude1", "offset1", "phase1", "output1"]
                if all(k in self.value for k in keys):
                    yield self.cxn.polarkrb_dg4000.set_sin(
                        1,
                        float(self.value["freq1"]),
                        float(self.value["amplitude1"]),
                        float(self.value["offset1"]),
                        float(self.value["phase1"]),
                    )
                    yield self.cxn.polarkrb_dg4000.set_output(1, bool(self.value["output1"]))
                if "ncycles1" in self.value:
                    yield self.cxn.polarkrb_dg4000.set_ncycles(1, int(self.value["ncycles1"]))
                if "FSKfreq1" in self.value:
                    yield self.cxn.polarkrb_dg4000.set_fskfreq(1, float(self.value["FSKfreq1"]))
                keys = ["freq2", "amplitude2", "offset2", "phase2", "output2"]
                if all(k in self.value for k in keys):
                    yield self.cxn.polarkrb_dg4000.set_sin(
                        2,
                        float(self.value["freq2"]),
                        float(self.value["amplitude2"]),
                        float(self.value["offset2"]),
                        float(self.value["phase2"]),
                    )
                    yield self.cxn.polarkrb_dg4000.set_output(2, bool(self.value["output2"]))
                if "ncycles2" in self.value:
                    yield self.cxn.polarkrb_dg4000.set_ncycles(2, int(self.value["ncycles2"]))
                # yield self.cxn.polarkrb_dg4000.set_ncycles(1,int(self.value['ncycles1']))
                # yield self.cxn.polarkrb_dg4000.set_ncycles(2,int(self.value['ncycles2']))
                # yield self.cxn.polarkrb_dg4000.set_gated(1,bool(self.value['gated1']))
                # yield self.cxn.polarkrb_dg4000.set_gated(2,bool(self.value['gated2']))
            except Exception as e:
                print(e)
