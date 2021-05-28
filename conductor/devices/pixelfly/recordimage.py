import sys
sys.path.append('../')
from generic_device.generic_parameter import GenericParameter

from twisted.internet.defer import inlineCallbacks, Deferred
from twisted.internet.reactor import callLater
from labrad.wrappers import connectAsync

from conductor_device.conductor_parameter import ConductorParameter

class RecordImage(ConductorParameter):
    priority = 1

    def __init__(self, config={}):
        super(RecordImage, self).__init__(config)
        self.value = [self.default_pixelfly]

    @inlineCallbacks
    def initialize(self):
        self.cxn = yield connectAsync()
        devices = yield self.cxn.polarkrb_pco.get_interface_list()
        try:
            yield self.cxn.polarkrb_pco.select_device(devices[0])
        except Exception as e:
            print(e)

    @inlineCallbacks
    def update(self):
        if self.value:
            try:
                if self.value["enable"]:
                    shot = yield self.cxn.imaging_logging.get_shot()
                    path = yield self.cxn.imaging_logging.get_path() + "pixelfly_{}.npz".format(shot)
                    yield self.cxn.polarkrb_pco.stop_record()
                    yield self.cxn.polarkrb_pco.set_exposure(self.value["exposure"])
                    yield self.cxn.polarkrb_pco.set_binning(self.value["binning"])
                    yield self.cxn.polarkrb_pco.set_exposure(self.value["interframing_enable"])
                    yield self.cxn.polarkrb_pco.set_trigger_mode("external exposure start & software trigger")
                    yield self.cxn.polarkrb_pco.record_and_save(path, n_images=self.value["n_images"], roi=(self.value["roi"] if "None" not in self.value["roi"] else None), timeout=None)
            except Exception as e:
                print(e)
