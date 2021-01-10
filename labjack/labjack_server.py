"""
### BEGIN NODE INFO
[info]
name = DG800
version = 1
description = server for LabJack T7 DAQ
instancename = %LABRADNODE%_labjack
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
from labjack import ljm
import pandas as pd
import numpy as np
import datetime
import json

class LabJackServer(LabradServer):
    """Provides access to LabJack T7 DAQ."""
    name = '%LABRADNODE%_labjack'

    def __init__(self):
        super(LabJackServer, self).__init__()

        config_fname = "../logging/logging_config.json"
        self.config = json.load(config_fname)['labjack']

        self.handle = ljm.openS("T7", "ANY", "ANY")

        info = ljm.getHandleInfo(self.handle)
        print("Opened a LabJack with Device type: %i, Connection type: %i,\n"
        "Serial number: %i, IP address: %s, Port: %i,\nMax bytes per MB: %i" %
        (info[0], info[1], info[2], ljm.numberToIP(info[3]), info[4], info[5]))

    
    def callback(self, handle):
        ret = ljm.eStreamRead(self.handle)[0]
        data = np.array(ret).reshape(-1, self.nchannels)
        data[:,1] = data[:,1]*65536+data[:,0]
        if self.start_time == 0:
            self.start_time = data[0,1]
        data[:,1] = (data[:,1] - self.start_time)/40E6
        with open(self.path, "a") as f:
            np.savetxt(f, data[:,1:], delimiter=',',header='',comments='',fmt="%f,"*(self.nchannels-1))
        self.reads -= 1
        if(self.reads == 0):
            ljm.eStreamStop(handle)

    def configureDeviceForTriggeredStream(self, triggerName):
        """Configure the device to wait for a trigger before beginning stream.

        @para handle: The device handle
        @type handle: int
        @para triggerName: The name of the channel that will trigger stream to start
        @type triggerName: str
        """
        address = ljm.nameToAddress(triggerName)[0]
        ljm.eWriteName(self.handle, "STREAM_TRIGGER_INDEX", address)

        # Clear any previous settings on triggerName's Extended Feature registers
        ljm.eWriteName(self.handle, "%s_EF_ENABLE" % triggerName, 0)

        # 5 enables a rising or falling edge to trigger stream
        ljm.eWriteName(self.handle, "%s_EF_INDEX" % triggerName, 5)

        # Enable
        ljm.eWriteName(self.handle, "%s_EF_ENABLE" % triggerName, 1)

    def configureLJMForTriggeredStream(self):
        ljm.writeLibraryConfigS(ljm.constants.STREAM_SCANS_RETURN, ljm.constants.STREAM_SCANS_RETURN_ALL_OR_NONE)
        ljm.writeLibraryConfigS(ljm.constants.STREAM_RECEIVE_TIMEOUT_MS, 0)
        # By default, LJM will time out with an error while waiting for the stream
        # trigger to occur.

    @setting(3, reads='i', scansPerRead='i', aScanList='*s', scanRate='v', savePath='s', triggerName='s', openMode='s')
    def setup_stream(self, c, reads, scansPerRead, aScanList, scanRate, savePath, triggerName, openMode='a+'):
        if(ljm.eReadAddress(self.handle, 4990, 1)): #STREAM_ENABLE
            ljm.eStreamStop(self.handle)
        if triggerName != "":
            self.configureLJMForTriggeredStream()
            self.configureDeviceForTriggeredStream(triggerName)
        else:
            ljm.writeLibraryConfigS(ljm.constants.STREAM_SCANS_RETURN, ljm.constants.STREAM_SCANS_RETURN_ALL)
            ljm.writeLibraryConfigS(ljm.constants.STREAM_RECEIVE_TIMEOUT_MODE, ljm.constants.STREAM_RECEIVE_TIMEOUT_MODE_CALCULATED)
            ljm.eWriteName(self.handle, "STREAM_TRIGGER_INDEX", 0)
        aScanList = ['CORE_TIMER', 'STREAM_DATA_CAPTURE_16'] + aScanList
        self.reads = reads
        self.nchannels = len(aScanList)
        self.path = savePath
        self.start_time = 0
        with open(savePath, openMode) as f:
            f.write('time,')
            [f.write('%s,' % i) for i in aScanList[2:]]
            f.write('\n')
        ljm.eStreamStart(self.handle, scansPerRead, self.nchannels, ljm.namesToAddresses(self.nchannels, aScanList)[0], scanRate)
        ljm.setStreamCallback(self.handle, self.callback)

    @setting(4, addr='s', returns='v')
    def read_register(self, c, addr):
        try:
            returnValue(ljm.eReadName(self.handle, addr))
        except Exception as e:
            print(e)
            returnValue(0.0)
        
    @setting(5, addr='s', val='v')
    def write_register(self, c, addr, val):
        try:
            ljm.eWriteName(self.handle, addr, val)
        except Exception as e:
            print(e)
        
    @setting(6, addr='s', returns='s')
    def read_register_string(self, c, addr):
        try:
            returnValue(ljm.eReadNameString(self.handle, addr))
        except Exception as e:
            print(e)
            returnValue("")

    @setting(7, addr='s', val='s')
    def write_register_string(self, c, addr, val):
        try:
            ljm.eWriteNameString(self.handle, addr, val)
        except Exception as e:
            print(e)

    @setting(8)
    def stop_stream(self, c):
        try:
            ljm.eStreamStop(self.handle)
        except Exception as e:
            print(e)

    @setting(9, path='s', idle='b')
    def set_shot(self, c, path, idle=False):
        fname = path+"labjack_"+datetime.now().strftime("%Y-%m-%d_%H-%M-%S.%f")+".csv"
        scan_list = [c["id"] for c in self.config["channels"]]
        if idle:
            self.setup_stream(None, self.config["idlemaxreads"], self.config["idlescansperread"], scan_list, self.config["idlerate"], fname, "")
        else:
            self.setup_stream(None, self.config["maxreads"], self.config["scansperread"], scan_list, self.config["scanrate"], fname, self.config["trigger"])
        

if __name__ == "__main__":
    from labrad import util
    util.runServer(LabJackServer())