"""
### BEGIN NODE INFO
[info]
name = DG800
version = 1
description = server for Rigol DG800 series AWGs
instancename = %LABRADNODE%_DG800

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
sys.path.append("../client_tools")
from connection import connection
from twisted.internet.defer import inlineCallbacks, returnValue

class DG800Server(LabradServer):
    """Provides access to Rigol DG800 series AWGs."""
    name = '%LABRADNODE%_DG800'

    def __init__(self):
        self.USB_server_name = 'polarkrb_usb'
        super(DG800Server, self).__init__()
        self.connect()
    
    @inlineCallbacks
    def connect(self):
        self.cxn = connection()
        yield self.cxn.connect()
        self.USB = yield self.cxn.get_server(self.USB_server_name)

    @setting(5, returns='*s')
    def get_devices(self, c):
        interfaces = yield self.USB.get_interface_list()
        self.devices = []
        for i in interfaces:
            self.select_device(c, i)
            id = yield self.USB.query('*IDN?')
            if "DG832" in id:
                self.devices.append(i)
        returnValue(self.devices)

    @setting(6, device='s')
    def select_device(self, c, device):
        self.USB.select_interface(device)

    @setting(7, channel='i', freq='v', amplitude='v', offset='v', phase='v')
    def set_sin(self, c, channel, freq, amplitude, offset, phase):
        yield self.USB.write(":SOUR%d:APPL:SIN %f,%f,%f,%f" % (channel, freq, amplitude, offset, phase))

    @setting(8, channel='i', enable='b')
    def set_output(self, c, channel, enable):
        if enable:
            stringthing = 'ON'
        else:
            stringthing = 'OFF'
        yield self.USB.write(":OUTP%d %s" % (channel, stringthing))

    @setting(9, channel='i', returns='*v')
    def get_sin(self, c, channel):
        out = yield self.USB.query(":SOUR%d:APPL?" % (channel))
        splits = out.replace('"','').split(',')
        if 'SIN' in splits[0]:
            returnValue([float(i) for i in splits[1:]])
        else:
            returnValue([0])

    @setting(10, channel='i', returns='b')
    def get_output(self, c, channel):
        stringthing = yield self.USB.query(":OUTP%d?" % (channel))
        out = 'ON' in stringthing
        returnValue(out)

if __name__ == '__main__':
    from labrad import util
    util.runServer(DG800Server())
