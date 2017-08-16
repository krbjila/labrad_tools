"""
### BEGIN NODE INFO
[info]
name = okfpga
version = 1.0
description = 
instancename = %LABRADNODE%_okfpga

[startup]
cmdline = %PYTHON% %FILE%
timeout = 20

[shutdown]
message = 987654321
timeout = 20
### END NODE INFO
"""
import json
import numpy as np
import os
import sys

import ok

from labrad.server import LabradServer, setting, Signal
from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.internet.threads import deferToThread

sys.path.append('../')
from server_tools.hardware_interface_server import HardwareInterfaceServer

SEP = os.path.sep

class OKFPGAServer(HardwareInterfaceServer):
    name = '%LABRADNODE%_okfpga'

    def refresh_available_interfaces(self):
        for device_id, device in self.interfaces.items():
            try: 
                device.GetDeviceID()
            except:
                del self.interfaces[device_id]

        fp = ok.FrontPanel()
        device_count = fp.GetDeviceCount()
        for i in range(device_count):
            serial = fp.GetDeviceListSerial(i)
            tmp = ok.FrontPanel()
            tmp.OpenBySerial(serial)
            device_id = tmp.GetDeviceID()
            print(device_id)
            tmp.LoadDefaultPLLConfiguration()
            self.interfaces[device_id] = tmp

    @setting(3, filename='s')
    def program_bitfile(self, c, filename):
        self.call_if_available('ConfigureFPGA', c, 'bit_files'+SEP+filename)
    
    @setting(11, wire='i', byte_array='s')
    def write_to_pipe_in(self, c, wire, byte_array):
        byte_array = json.loads(byte_array)
        self.call_if_available('WriteToPipeIn', c, wire, bytearray(byte_array))

    @setting(12, wire='i', value='i')
    def set_wire_in(self, c, wire, value):
        self.call_if_available('SetWireInValue', c, wire, value)
    
    @setting(13)
    def update_wire_ins(self, c):
        self.call_if_available('UpdateWireIns', c)

if __name__ == "__main__":
    from labrad import util
    util.runServer(OKFPGAServer())
