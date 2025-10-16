"""
Provides access to LabJack T7 DAQ.
"""

r"""
### BEGIN NODE INFO
[info]
name = labjack
version = 1
description = server for LabJack T7 DAQ
instancename = %LABRADNODE%_labjack
[startup]
cmdline = "C:\\Users\\polarkrb2\\.conda\\envs\\labrad-py310\\python.exe" "%FILE%"
timeout = 20
[shutdown]
message = 987654321
timeout = 20
### END NODE INFO
"""


import sys
from labrad.server import LabradServer, setting
from labrad.util import getNodeName
sys.path.append("../client_tools")
from connection import connection
from twisted.internet.defer import inlineCallbacks, returnValue
from threading import Thread
from labjack import ljm
import pandas as pd
import numpy as np
from datetime import datetime
import json
import os
import struct

class LabJackServer(LabradServer):
    """Provides access to LabJack T7 DAQ."""
    name = '%LABRADNODE%_labjack'

    def __init__(self):
        self.name = "{}_labjack".format(getNodeName())
        super(LabJackServer, self).__init__()

        self.handle = ljm.openS("T7", "ETHERNET", "10.1.107.69")

        info = ljm.getHandleInfo(self.handle)
        print("Opened a LabJack with Device type: %i, Connection type: %i,\n"
        "Serial number: %i, IP address: %s, Port: %i,\nMax bytes per MB: %i" %
        (info[0], info[1], info[2], ljm.numberToIP(info[3]), info[4], info[5]))

    def stopServer(self):
        """
        Run when the LabRAD server is stopped. Closes the connection to the LabJack.
        """
        ljm.close(self.handle)

    @inlineCallbacks
    @setting(10, name='s', value='v')
    def write_name(self, c, name, value):
        """
        Write a value to a named register on the LabJack.
        """
        ljm.eWriteName(self.handle, name, value)

    @inlineCallbacks
    @setting(11, name='s', returns='v')
    def read_name(self, c, name):
        """
        Read a value from a named register on the LabJack.
        """
        value = yield ljm.eReadName(self.handle, name)
        returnValue(value)

    @inlineCallbacks
    @setting(12, address='i', value='v')
    def write_address(self, c, address, value):
        """
        Write a value to a register on the LabJack.
        """
        ljm.eWriteAddress(self.handle, address, value)

    @inlineCallbacks
    @setting(13, address='i', returns='v')
    def read_address(self, c, address):
        """
        Read a value from a register on the LabJack.
        """
        value = yield ljm.eReadAddress(self.handle, address)
        returnValue(value)

    @inlineCallbacks
    @setting(14, names='*s', values='*v')
    def write_names(self, c, names, values):
        """
        Write values to multiple named registers on the LabJack.
        """
        ljm.eWriteNames(self.handle, len(names), names, values)

    @inlineCallbacks
    @setting(15, names='*s', returns='*v')
    def read_names(self, c, names):
        """
        Read values from multiple named registers on the LabJack.
        """
        values = yield ljm.eReadNames(self.handle, len(names), names)
        returnValue(values)

    @inlineCallbacks
    @setting(16, addresses='*i', values='*v')
    def write_addresses(self, c, addresses, values):
        """
        Write values to multiple registers on the LabJack.
        """
        ljm.eWriteAddresses(self.handle, len(addresses), addresses, values)

    @inlineCallbacks
    @setting(17, addresses='*i', returns='*v')
    def read_addresses(self, c, addresses):
        """
        Read values from multiple registers on the LabJack.
        """
        values = yield ljm.eReadAddresses(self.handle, len(addresses), addresses)
        returnValue(values)
    

        

if __name__ == "__main__":
    from labrad import util
    util.runServer(LabJackServer())