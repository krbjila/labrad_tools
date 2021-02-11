"""
### BEGIN NODE INFO
[info]
name = dg800
version = 1
description = server for Rigol DG800 series AWGs
instancename = %LABRADNODE%_dg800

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

class DG800Server(LabradServer):
    """Provides access to Rigol DG800 series AWGs."""
    name = '%LABRADNODE%_dg800'

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

    @setting(11, channel='i', impedance='i', inf='b', low='b')
    def set_impedance(self, c, channel, impedance=50, inf=False, low=False):
        if inf:
            yield self.USB.write(":OUTP%d:IMP INF" % (channel))

        elif low:
            yield self.USB.write(":OUTP%d:IMP MIN" % (channel))

        else:
            yield self.USB.write(":OUTP%d:IMP %d" % (channel, impedance))

    @setting(12, channel='i', ncycles='i')
    def set_ncycles(self, c, channel, ncycles):
        yield self.USB.write(":SOUR%d:BURS:NCYC %d" % (channel, ncycles))

    @setting(13, channel='i', gated='b')
    def set_gated(self, c, channel, gated):
        if gated:
            yield self.USB.write(":SOUR%d:BURS:MODE GAT" % (channel))
        else:
            yield self.USB.write(":SOUR%d:BURS:MODE TRIG" % (channel))

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
