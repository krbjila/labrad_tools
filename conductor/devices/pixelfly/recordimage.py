import sys
sys.path.append('../')
from generic_device.generic_parameter import GenericParameter

from twisted.internet.defer import inlineCallbacks, Deferred
from twisted.internet.reactor import callLater
from labrad.wrappers import connectAsync

from datetime import datetime
import re
import os
from time import sleep

from conductor_device.conductor_parameter import ConductorParameter

class Recordimage(ConductorParameter):
    priority = 1

    def __init__(self, config={}):
        super(Recordimage, self).__init__(config)
        self.value = [self.default_recordimage]

    @inlineCallbacks
    def initialize(self):
        self.cxn = yield connectAsync()
        try:
            self.server = yield self.cxn.polarkrb_pco
            devices = yield self.server.get_interface_list()
            yield self.server.select_interface(devices[0])
        except Exception as e:
            print("Pixelfly server not connected: {}".format(e))

    @inlineCallbacks
    def update  (self):
        if self.value:
            try:
                if self.value["enable"]:
                    yield self.server.stop_record()
                    sleep(0.1)
                    yield self.server.set_exposure(self.value["exposure"])
                    yield self.server.set_binning(self.value["binning"])
                    yield self.server.set_interframing_enabled(self.value["interframing_enable"] != 0)
                    yield self.server.set_trigger_mode("external exposure start & software trigger")
                    sleep(0.1)
                    path = yield self.server.get_fname()
                    if "None" in self.value["roi"]:
                        yield self.server.record_and_save(path, self.value["n_images"])
                    else:
                        yield self.server.record_and_save(path, self.value["n_images"], roi=self.value["roi"])
                else:
                    if self.server.is_running():
                        self.server.stop_record()
            except Exception as e:
                print("Could not update Pixelfly: {}".format(e))
