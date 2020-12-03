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
from datetime import datetime
from labrad.server import LabradServer, setting
from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.internet.task import LoopingCall

class ag34410aServer(LabradServer):
    """Provides access to Rigol DG800 series AWGs."""
    name = '%LABRADNODE%_ag34410a'

    def __init__(self):
        self.USB_server_name = 'polarkrb_usb'
        LabradServer.__init__(self)
    
    @inlineCallbacks
    def initServer(self):
        update_time = 0.05 # s
        self.USB = yield self.client.servers[self.USB_server_name]
        devices = yield self.get_devices(None)
        self.logging = self.client.servers['imaging_logging']
        self.logging.set_name("multimeter")
        if len(devices):
            self.select_device(None, devices[0])
            self.logging_call = LoopingCall(self.log_multimeter)
            self.logging_call.start(update_time, now=False)

    @setting(5, returns='*s')
    def get_devices(self, c):
        interfaces = yield self.USB.get_interface_list()
        self.devices = []
        for i in interfaces:
            self.select_device(c, i)
            id = yield self.USB.query('*IDN?\n')
            if "34410" in id:
                self.devices.append(i)
        returnValue(self.devices)

    @setting(6, device='s')
    def select_device(self, c, device):
        self.USB.select_interface(device)

    @inlineCallbacks
    @setting(10, returns='v')
    def read(self, c):
        val = yield self._read()
        returnValue(val)

    @inlineCallbacks
    def _read(self):
        has_points = yield self.USB.query("DATA:POIN?\n")
        out = -9000.0
        if int(has_points):
            val = yield self.USB.query("FETC?\n")
            yield self.USB.write("INIT\n")
            out = float(val)
        returnValue(out)
    
    @inlineCallbacks
    def log_multimeter(self):
        try:
            val = yield self._read()
        except Exception as e:
            print("Could not get value from multimeter: %s" % (e))
            return
        if val != -9000.0:
            self.logging.log("%s" % val, datetime.now())

if __name__ == '__main__':
    from labrad import util
    util.runServer(ag34410aServer())
