import sys
sys.path.append('../')
from generic_device.generic_parameter import GenericParameter

from twisted.internet.defer import inlineCallbacks, Deferred
from twisted.internet.reactor import callLater
from labrad.wrappers import connectAsync

from datetime import datetime
import re

from conductor_device.conductor_parameter import ConductorParameter

class Recordimage(ConductorParameter):
    priority = 1
    path_base = "K:/data/{}/Pixelfly/"
    pattern = r"pixelfly_(\d+).npz"
    fname_base = "pixelfly_{}.npz"

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
                if self.value["enable"] > 0:
                    path = path_base.format(datetime.now().strftime('%Y/%m/%Y%m%d'))
                    os.makedirs(path, exist_ok=True)
                    file_number = 0
                    for f in os.listdir(path):
                        match = re.fullmatch(pattern, f)
                        if match:
                            file_number = max(file_number, 1+int(match.groups()[0]))
                    path += fname_base.format(file_number)
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
