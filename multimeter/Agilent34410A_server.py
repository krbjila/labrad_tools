"""
Provides access to Agilent 34410A multimeters.

..
    ### BEGIN NODE INFO
    [info]
    name = ag34410a
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
from labrad.util import getNodeName
from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.internet.task import LoopingCall

class ag34410aServer(LabradServer):
    """Provides access to Agilent 34410A multimeters."""
    name = '%LABRADNODE%_ag34410a'

    def __init__(self):
        LabradServer.__init__(self)
    
    @inlineCallbacks
    def initServer(self):
        """
        initServer(self)

        Lists connected multimeters, if any, and connects to the first one.
        """
        update_time = 0.25 # s
        self.USB_server_name = '{}_usb'.format(getNodeName())
        self.USB = yield self.client.servers[self.USB_server_name]
        devices = yield self.get_devices(None)
        self.logging = self.client.servers['imaging_logging']
        self.logging.set_name("multimeter_{}".format(getNodeName()))
        if len(devices):
            self.select_device(None, devices[0])
            self.logging_call = LoopingCall(self.log_multimeter)
            self.logging_call.start(update_time, now=False)

    @setting(5, returns='*s')
    def get_devices(self, c):
        """
        get_devices(self, c)
        
        Lists connected multimeters. Note that the function connects to each device to check its ID.

        Args:
            c: A LabRAD context (which is passed on to passed to :meth:`ag34410aServer.select_device`)

        Yields:
            A list of strings corresponding to the IDs of connected multimeters
        """
        interfaces = yield self.USB.get_interface_list()
        self.devices = []
        for i in interfaces:
            self.select_device(c, i)
            id = yield self.USB.query('*IDN?\n')
            if "34410" in id:
                print("Connected to device {}".format(id))
                self.devices.append(i)
        returnValue(self.devices)

    @setting(6, device='s')
    def select_device(self, c, device):
        """
        select_device(self, c, device)
        
        Select a connected multimeter

        Args:
            c: A LabRAD context (not used)
            device (string): The ID of the multimeter to connect to, as returned by :meth:`ag34410aServer.get_devices`
        """
        self.USB.select_interface(device)

    @inlineCallbacks
    @setting(10, returns='v')
    def read(self, c):
        """
        read(self, c)
        
        Reads the current data from the multimeter

        Args:
            c: A LabRAD context (not used)

        Yields:
            [type]: [description]
        """
        val = yield self._read()
        returnValue(val)

    @inlineCallbacks
    def _read(self):
        has_points = yield self.USB.query("DATA:POIN?\n")
        print(has_points)
        out = -9000.0
        if int(has_points):
            print("Data ready: {}".format(int(has_points)))
            val = yield self.USB.query("FETC?\n")
            yield self.USB.write("INIT\n")
            out = float(val)
        returnValue(out)
    
    @inlineCallbacks
    def log_multimeter(self):
        """
        log_multimeter(self)
        
        Logs the current multimeter data using the #TODO: logging server link
        """
        try:
            val = yield self._read()
        except Exception as e:
            print("Could not get value from multimeter: %s" % (e))
            return
        if val != -9000.0:
            self.logging.log("%s" % val, datetime.now())
            print("logging value {}".format(val))

if __name__ == '__main__':
    from labrad import util
    util.runServer(ag34410aServer())
