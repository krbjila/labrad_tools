"""
### BEGIN NODE INFO
[info]
name = DG800
version = 1
description = server for Highfinesse WS-7 Wavemeter
instancename = %LABRADNODE%_wavemeter
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
from twisted.intenet.task import LoopingCall
from twisted.internet import reactor
import urllib, json

class WavemeterServer(LabradServer):
    """Provides access to Highfinesse WS-7 Wavemeter. Requires that the server from https://github.com/stepansnigirev/py-ws7 be running"""
    name = '%LABRADNODE%_wavemeter'
    url = 'http://localhost:8000/wavemeter'
    update_rate = 100

    def __init__(self):
        self.USB_server_name = 'wavemeterlaptop_wavemeter'
        super(WavemeterServer, self).__init__()
        lc = LoopingCall(self.update)
        lc.start(1/update_rate)

    def update(self):
        response = urllib.urlopen(url)
        self.data = json.dumps(response)

    @setting(5, returns='s')
    def get_wavelengths(self, c):
        returnValue = self.data

if __name__ == '__main__':
    from labrad import util
    util.runServer(DG800Server())