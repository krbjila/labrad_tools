"""
### BEGIN NODE INFO
[info]
name = picomotor
version = 1.0
description = 
instancename = picomotor

[startup]
cmdline = %PYTHON% %FILE%
timeout = 20

[shutdown]
message = 987654321
timeout = 5
### END NODE INFO
"""

import sys

from labrad.server import Signal, setting

from twisted.internet.defer import DefferedLock

sys.path.append('../')
from server_tools.device_server import DeviceServer
from server_tools.decorators import quickSetting

UPDATE_ID = 699043

class PicomotorServer(DeviceServer):
    """
    picomotor LabRAD server
    """
    update = Signal(UPDATE_ID, 'signal: update', 's')
    name = 'picomotor'
    
    def __init__(self, config_path='./config.json'):
        PicomotorServer.__init__(self)
        self.socket_lock = DeferredLock()
    
#    @quickSetting(11, 'i')
#    def position(self, c, position=None):
#        """ get or set position """

    @setting(11, position='i', return='i')
    def position(self, c, position=None):
        """ get or set position """
        yield self.socket_lock.acquire()
        device = self.get_device(c)
        if position is not None:
            yield device.set_position(position)
        position = yield device.get_position()
        yield self.socket_lock.release()
        returnValue(position)
    
if __name__ == '__main__':
    from labrad import util
    util.runServer(PicomotorServer())
