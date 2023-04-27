"""
Provides access to Highfinesse WS-7 Wavemeter.

..
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
from labrad.server import LabradServer, setting, Signal
sys.path.append("../client_tools")
# from connection import connection
from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.internet.task import LoopingCall
from twisted.internet import reactor
from labrad.util import getNodeName
import json
import pycurl
from io import BytesIO

class WavemeterServer(LabradServer):
    """Provides access to Highfinesse WS-7 Wavemeter. Requires that the server from https://github.com/stepansnigirev/py-ws7 be running. The URL is hardcoded to localhost port 8000."""
    name = '%LABRADNODE%_wavemeter'
    url = 'http://localhost:8000/wavemeter/api/'

    onSetSetpoint = Signal(314159, 'signal: set setpoint', 'd')

    def __init__(self):
        self.name = '{}_wavemeter'.format(getNodeName())
        self.data = ''
        super(WavemeterServer, self).__init__()

    def update(self):
        """
        update(self)

        Updates internal state with the latest wavelengths from the wavemeter
        """
        try:
            buffer = BytesIO()
            c = pycurl.Curl()
            c.setopt(c.URL, self.url)
            c.setopt(c.WRITEFUNCTION, buffer.write)
            c.perform()
            c.close()
            body = buffer.getvalue()
            self.data = json.dumps(body.decode('iso-8859-1'))
        except Exception as e:
            print("Could not connect to wavemeter: %s" % (e))
    
    @inlineCallbacks
    @setting(5, returns='s')
    def get_wavelengths(self, c):
        """
        get_wavelengths(self, c)
        
        Updates and returns data from the wavemeter

        Args:
            c: A LabRAD context (not used)

        Yields:
            Returns a string containing the latest wavemeter data encoded as a JSON.
        """
        yield self.update()
        returnValue(self.data)

    @inlineCallbacks
    @setting(6, returns='d')
    def set_setpoint(self, c, setpoint):
        """
        set_setpoint(self, c, setpoint)

        Sets the wavemeter lock setpoint

        Args:
            c: A LabRAD context (not used)
            setpoint: The setpoint (THz)
        Yields:
            Returns the setpoint
        """
        self.onSetSetpoint(setpoint)
        returnValue(setpoint)
        

if __name__ == '__main__':
    from labrad import util
    util.runServer(WavemeterServer())