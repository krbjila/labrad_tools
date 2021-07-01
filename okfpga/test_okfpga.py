"""
### BEGIN NODE INFO
[info]
name = test_okfpga
version = 1.0
description = Mock up server for working on sequencer without being connected to hardware
instancename = test_okfpga

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

from labrad.server import LabradServer, setting, Signal
from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.internet.threads import deferToThread

sys.path.append('../')
from server_tools.hardware_interface_server import HardwareInterfaceServer

SEP = os.path.sep

class TestOkfpga(HardwareInterfaceServer):
    name = 'test_okfpga'

    def refresh_available_interfaces(self):
        # for device_id, device in self.interfaces.items():
        #     try: 
        #         device.GetDeviceID()
        #     except:
        #         del self.interfaces[device_id]

        # fp = ok.FrontPanel()
        # device_count = fp.GetDeviceCount()
        # for i in range(device_count):
        #     serial = fp.GetDeviceListSerial(i)
        #     tmp = ok.FrontPanel()
        #     tmp.OpenBySerial(serial)
        #     device_id = tmp.GetDeviceID()
        #     print(device_id)
        #     tmp.LoadDefaultPLLConfiguration()
        #     self.interfaces[device_id] = tmp
        self.interfaces = {
            'KRbDigi01': 'ABCD',
            'KRbDigi02': 'EFGH',
            'KRbAnlg01': 'I',
            'KRbAnlg02': 'J',
            'KRbAnlg03': 'K',
            'KRbAnlg04': 'L',
            'KRbAnlg05': 'M',
            'KRbAnlg06': 'N',
            'KRbStable01': 'S',
        }

    @setting(3, filename='s')
    def program_bitfile(self, c, filename):
        # self.call_if_available('ConfigureFPGA', c, 'bit_files'+SEP+filename)
        pass
    
    @setting(11, wire='i', byte_array='s')
    def write_to_pipe_in(self, c, wire, byte_array):
        # byte_array = json.loads(byte_array)
        # self.call_if_available('WriteToPipeIn', c, wire, bytearray(byte_array))
        pass

    @setting(12, wire='i', value='i')
    def set_wire_in(self, c, wire, value):
        # self.call_if_available('SetWireInValue', c, wire, value)
        pass
    
    @setting(13)
    def update_wire_ins(self, c):
        # self.call_if_available('UpdateWireIns', c)
        pass

def main(): 
    from labrad import util
    util.runServer(TestOkfpga())

if __name__ == "__main__":
    main()
