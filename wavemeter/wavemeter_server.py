"""
### BEGIN NODE INFO
[info]
name = wavemeter
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
# from connection import connection
from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.internet.task import LoopingCall
from twisted.internet import reactor
# import urllib
import json
import pycurl
from io import BytesIO

class WavemeterServer(LabradServer):
    """Provides access to Highfinesse WS-7 Wavemeter. Requires that the server from https://github.com/stepansnigirev/py-ws7 be running"""
    name = '%LABRADNODE%_wavemeter'
    url = 'http://localhost:8000/wavemeter/api/'
    update_rate = 100

    def __init__(self):
        self.name = 'wavemeterlaptop_wavemeter'
        super(WavemeterServer, self).__init__()
        # lc = LoopingCall(self.update)
        # lc.start(1/self.update_rate)

    def update(self):
        # response = urllib.urlopen(self.url)
        # self.data = json.dumps(response.read())
        # response.close()
        buffer = BytesIO()
        c = pycurl.Curl()
        c.setopt(c.URL, self.url)
        c.setopt(c.WRITEDATA, buffer)
        c.perform()
        c.close()
        body = buffer.getvalue()
        self.data = json.dumps(body.decode('iso-8859-1'))
        print(self.data)
    
    @inlineCallbacks
    @setting(5, returns='s')
    def get_wavelengths(self, c):
        yield self.update()
        returnValue(self.data)

if __name__ == '__main__':
    from labrad import util
    util.runServer(WavemeterServer())