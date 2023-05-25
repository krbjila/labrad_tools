"""
Interface for Thorlabs Kinesis hardware.

..
    ### BEGIN NODE INFO
    [info]
    name = kinesis
    version = 1.0
    description = 
    instancename = %LABRADNODE%_kinesis

    [startup]
    cmdline = %PYTHON3% %FILE%
    timeout = 20

    [shutdown]
    message = 987654321
    timeout = 20
    ### END NODE INFO
"""

import os, sys
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..'))
from server_tools.device_server import DeviceServer

from twisted.internet.defer import inlineCallbacks, returnValue
from labrad.server import setting 

class KinesisServer(DeviceServer):
    name = '%LABRADNODE%_kinesis'

    @inlineCallbacks
    def init_connection(self, device):
        print('connection opened: {} - {}'.format(device.servername, device.address))
        self.open_connections[device.connection_name] = yield device.connection_name

    @inlineCallbacks
    @setting(10, 'home')
    def home(self, c):
        """Home the stage."""
        device = self.get_device(c)
        yield device.home()

    @inlineCallbacks
    @setting(11, 'move_to', position='v')
    def move_to(self, c, position):
        """Move to a position."""
        device = self.get_device(c)
        yield device.move_to(position)

    @inlineCallbacks
    @setting(12, 'move_by', displacement='v')
    def move_by(self, c, displacement):
        """Move by a displacement."""
        device = self.get_device(c)
        yield device.move_by(displacement)

    @inlineCallbacks
    @setting(13, 'get_position', returns='v')
    def get_position(self, c):
        """Get the current position."""
        device = self.get_device(c)
        position = yield device.get_position()
        returnValue(position)
        

if __name__ == "__main__":
    from labrad import util
    config_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'config.json')
    util.runServer(KinesisServer(config_path=config_path))
