"""
### BEGIN NODE INFO
[info]
name = status
version = 1.1
description =  
instancename = %LABRADNODE%_status

[startup]
cmdline = %PYTHON% %FILE%
timeout = 20

[shutdown]
message = 987654321
timeout = 20
### END NODE INFO
"""
import sys
import os
from time import sleep

from labrad.server import LabradServer, setting, Signal
from twisted.internet.defer import inlineCallbacks, returnValue
from serial import Serial
import serial.tools.list_ports

import subprocess

class StatusServer(LabradServer):
    """ Status of running widgets """
    name = '%LABRADNODE%_status'
    
    def __init__(self):
        LabradServer.__init__(self)
        self.startClients()

    def startClients(self): 

__server__ = StatusServer()

if __name__ == '__main__':
    from labrad import util
    util.runServer(__server__)
