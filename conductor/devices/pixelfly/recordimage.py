import sys
sys.path.append('../')
from generic_device.generic_parameter import GenericParameter

from twisted.internet.defer import inlineCallbacks, Deferred
from twisted.internet.reactor import callLater
from labrad.wrappers import connectAsync

from conductor_device.conductor_parameter import ConductorParameter

class Recordimage(ConductorParameter):
    priority = 1

    def __init__(self, config={}):
        super(Recordimage, self).__init__(config)
        self.value = [self.default_recordimage]

    @inlineCallbacks
    def initialize(self):
        self.cxn = yield connectAsync()
        devices = yield self.cxn.polarkrb_pco.get_interface_list()
        try:
            yield self.cxn.polarkrb_pco.select_interface(devices[0])
        except Exception as e:
            print(e)

    @inlineCallbacks
    def update(self):
        if self.value:
            try:
                if self.value["enable"]:
                    # shot = yield self.cxn.imaging_logging.get_shot()
                    # path = yield self.cxn.imaging_logging.get_path()
                    # path += "pixelfly_{}.npz".format(shot)
                    path = "C:/Users/krbji/Desktop/pixelfly_0.npz"
                    yield self.cxn.polarkrb_pco.stop_record()
                    yield self.cxn.polarkrb_pco.set_exposure(self.value["exposure"])
                    yield self.cxn.polarkrb_pco.set_binning(self.value["binning"])
                    yield self.cxn.polarkrb_pco.set_exposure(self.value["interframing_enable"])
                    yield self.cxn.polarkrb_pco.set_trigger_mode("external exposure start & software trigger")
                    if "None" in self.value["roi"]:
                        yield self.cxn.polarkrb_pco.record_and_save(path, self.value["n_images"])
                    else:
                        yield self.cxn.polarkrb_pco.record_and_save(path, self.value["n_images"], roi=self.value["roi"])
            except Exception as e:
                print(e)
