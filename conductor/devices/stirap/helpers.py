import sys
sys.path.append('../')

from twisted.internet.defer import inlineCallbacks
from labrad.wrappers import connectAsync

from conductor_device.conductor_parameter import ConductorParameter

class STIRAPDevice(ConductorParameter):
    """
    Conductor parameter for controlling STIRAP DDS. Individual DDSs should subclass this. The configuration for which hardware a conductor parameter communicates with is set in :mod:`conductor.conductor`'s `config.json <https://github.com/krbjila/labrad_tools/blob/master/conductor/config.json>`_.

    Data format:::

        [...]

    See documentation for :mod:`stirap_dds.stirap_server` for the correct format for the ``program`` and ``profile`` lists.

    TODO: Finish documenting this.
    """
    priority = 1
    value_type = 'list'

    def __init__(self, channel, config={}):
        super(STIRAPDevice, self).__init__(config)
        self.channel = channel
        try:
            self.value = self.default_freq
        except Exception as e:
            print("No default STIRAP frequency set.")
            self.value = None

    @inlineCallbacks
    def initialize(self):
        self.cxn = yield connectAsync()

        try:
            self.server = self.cxn.stirap
        except AttributeError:
            # Log a warning that the server can't be found.
            # Conductor will throw an error and remove the parameter
            print("STIRAP parameter error: STIRAP server not connected.")


    @inlineCallbacks
    def update(self):
        if self.value:
            try:
                yield self.server.set_eom_freqs(self.channel, self.value)
            except Exception as e:
                print(e)
