import os, sys
from twisted.internet.defer import inlineCallbacks, returnValue

sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), '../..'))
from server_tools.device_server import DeviceWrapper

from pylablib.devices import Thorlabs


class Stage(DeviceWrapper):
    def __init__(self, config):

        # Default values
        self.scale = 1.0 # steps per unit
        self.connection_type = 'Kinesis'

        # Non-default values
        for key, value in config.items():
            setattr(self, key, value)

        self.address = self.serial
        super(Stage, self).__init__({})
    
    @inlineCallbacks
    def initialize(self):
        devices = yield Thorlabs.list_kinesis_devices()
        self.stage = None
        if self.serial in [d[0] for d in devices]:
            self.stage = yield Thorlabs.KinesisMotor(self.serial, scale=self.scale)
        else:
            raise(LookupError('Device {} not found. Available devices are {}'.format(self.serial, devices)))
        
    # @inlineCallbacks
    # def set_enabled(self, enabled):
    #     yield self.stage.set_enabled(enabled)
    
    @inlineCallbacks
    def home(self):
        yield self.stage.home()

    @inlineCallbacks
    def move_to(self, position):
        yield self.stage.move_to(position)

    @inlineCallbacks
    def move_by(self, displacement):
        yield self.stage.move_by(displacement)

    @inlineCallbacks
    def get_position(self):
        position = yield self.stage.get_position()
        returnValue(position)
