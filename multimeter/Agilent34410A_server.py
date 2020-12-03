"""
### BEGIN NODE INFO
[info]
name = dg800
version = 1
description = server for Agilent 34410A multimeter
instancename = %LABRADNODE%_ag34410a

[startup]
cmdline = %PYTHON% %FILE%
timeout = 20

[shutdown]
message = 987654321
timeout = 20
### END NODE INFO
"""
import sys
from labrad.server import LabradServer, setting
from twisted.internet.defer import inlineCallbacks, returnValue

class ag34410aServer(LabradServer):
    """Provides access to Rigol DG800 series AWGs."""
    name = '%LABRADNODE%_ag34410a'

    def __init__(self):
        self.USB_server_name = 'imaging_usb'
        LabradServer.__init__(self)
    
    @inlineCallbacks
    def initServer(self):
        self.USB = yield self.client.servers[self.USB_server_name]

    @setting(5, returns='*s')
    def get_devices(self, c):
        interfaces = yield self.USB.get_interface_list()
        self.devices = []
        for i in interfaces:
            self.select_device(c, i)
            id = yield self.USB.query('*IDN?')
            if "34410" in id:
                self.devices.append(i)
        returnValue(self.devices)

    @setting(6, device='s')
    def select_device(self, c, device):
        self.USB.select_interface(device)

    @setting(10, returns='s')
    def read(self, c):
        stringthing = yield self.USB.query("R?")
        # out = float(stringthing)
        returnValue(stringthing)

if __name__ == '__main__':
    from labrad import util
    util.runServer(ag34410aServer())
