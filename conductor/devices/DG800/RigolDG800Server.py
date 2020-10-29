"""
### BEGIN NODE INFO
[info]
name = DG800
version = 1
description = 
instancename = %LABRADNODE%_DG800

[startup]
cmdline = %PYTHON% %FILE%
timeout = 20

[shutdown]
message = 987654321
timeout = 20
### END NODE INFO
"""
from gpib_server import USBServer

class DG800Server(USBServer):
    def __init__(self):
        self.name = '%LABRADNODE%_DG800'
        # get available devices

    @setting(7, channel='i', freq='v', amplitude='v', offset='v', phase='v', returns='')
    def set_sin(self, c, channel, freq, amplitude, offset, phase):
        self.write(c, ":SOUR%d:APPL:SIN %f,%f,%f,%f" % (channel, freq, ampl, offset, phase))

    @setting(8, channel='i', offset='b', returns='')
    def set_output(self, c, channel, enable):
        return self.write(c, ":OUTP%d %s" % (channel, enable ? 'ON' : 'OFF'))

    @setting(9, channel='i', returns='s')
    def get_sin(self, c, channel, freq):
        return self.query(c, ":SOUR%d:APPL?" % (channel))

    @setting(10, channel='i', returns='b')
    def get_output(self, c, channel):
        return 'ON' in self.query(c, ":OUTP%d?" % (channel))

if __name__ == '__main__':
    from labrad import util
    util.runServer(DG800Server())
