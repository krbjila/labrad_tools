import sys
sys.path.append('../')

from twisted.internet.defer import inlineCallbacks
from labrad.wrappers import connectAsync

from conductor_device.conductor_parameter import ConductorParameter

class KinesisDevice(ConductorParameter):
    """
    Conductor parameter for controlling Kinesis stages. Individual stages should subclass this. The configuration for which hardware a conductor parameter communicates with is set in :mod:`conductor.conductor`'s `config.json <https://github.com/krbjila/labrad_tools/blob/master/conductor/config.json>`_.

    Data format:::

        [...]
    """
    priority = 3
    value_type = 'single'

    def __init__(self, server_name, channel, config={}):
        super(KinesisDevice, self).__init__(config)
        self.channel = channel
        self.server_name = server_name
        self.value = None

    @inlineCallbacks
    def initialize(self):
        self.cxn = yield connectAsync()

        try:
            self.server = self.cxn[self.server_name]
        except AttributeError:
            # Log a warning that the server can't be found.
            # Conductor will throw an error and remove the parameter
            print("Kinesis parameter error: server not connected.")
        yield self.server.select_device(self.channel)
        yield self.server.enable()
        yield self.server.home()

    @inlineCallbacks
    def update(self):
        if self.value:
            try:
                yield self.server.select_device(self.channel)
                self.server.move_to(self.value)
                # yield self.server.move_sequence(self.value)
            except Exception as e:
                print(e)
