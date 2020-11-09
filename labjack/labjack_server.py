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

class LabJackServer(LabradServer):
    """Provides access to LabJack T7 DAQ."""
    name = '%LABRADNODE%_labjack'

    def __init__(self):
        super(LabJackServer, self).__init__()
        self.handle = ljm.openS("T7", "ANY", "ANY")
    
    def callback(self, handle):
        ret = ljm.eStreamRead(self.handle)[0]
        data = np.array(ret).reshape(-1, self.nchannels)
        data[:,1] = data[:,1]*65536+data[:,0]
        if self.start_time == 0:
            self.start_time = data[0,1]
        data[:,1] -= self.start_time
        with open(self.path, "a") as f:
            np.savetxt(f, data[:,1:], delimiter=',',header='',comments='',fmt="%.0f," + "%f,"*(self.nchannels-2))
        self.reads -= 1
        if(self.reads == 0):
            ljm.eStreamStop(handle)

    @setting(3, reads='i', scansPerRead='i', aScanList='*s', scanRate='v', savePath='s', triggerName='s')
    def setup_stream(self, c, reads, scansPerRead, aScanList, scanRate, savePath, triggerName):
        if(ljm.eReadAddress(self.handle, 4990, 1)): #STREAM_ENABLE
            ljm.eStreamStop(self.handle)
        if triggerName != "":
            # Configure LJM functions to return immediately and not time out waiting for data
            ljm.writeLibraryConfigS(ljm.constants.STREAM_SCANS_RETURN, ljm.constants.STREAM_SCANS_RETURN_ALL_OR_NONE)
            ljm.writeLibraryConfigS(ljm.constants.STREAM_RECEIVE_TIMEOUT_MS, 0)
            
            address = ljm.nameToAddress(triggerName)[0]
            ljm.eWriteName(self.handle, "STREAM_TRIGGER_INDEX", address);

            # Clear any previous settings on triggerName's Extended Feature registers
            ljm.eWriteName(self.handle, "%s_EF_ENABLE" % triggerName, 0);
            # 5 enables a rising or falling edge to trigger stream
            ljm.eWriteName(self.handle, "%s_EF_INDEX" % triggerName, 5);
            # Enable trigger
            ljm.eWriteName(self.handle, "%s_EF_ENABLE" % triggerName, 1);
        else:
            ljm.writeLibraryConfigS(ljm.constants.STREAM_SCANS_RETURN, ljm.constants.STREAM_SCANS_RETURN_ALL)
            ljm.writeLibraryConfigS(ljm.constants.STREAM_RECEIVE_TIMEOUT_MODE, ljm.constants.STREAM_RECEIVE_TIMEOUT_MODE_CALCULATED)
            ljm.eWriteName(self.handle, "STREAM_TRIGGER_INDEX", 0);
        aScanList = ['CORE_TIMER', 'STREAM_DATA_CAPTURE_16'] + aScanList
        self.reads = reads
        self.nchannels = len(aScanList)
        self.path = savePath
        self.start_time = 0
        with open(savePath, "w+") as f:
            f.write('CORE_TIMER,')
            [f.write('%s,' % i) for i in aScanList[2:]]
            f.write('\n')
        ljm.eStreamStart(self.handle, scansPerRead, self.nchannels, ljm.namesToAddresses(self.nchannels, aScanList)[0], scanRate)
        ljm.setStreamCallback(self.handle, self.callback)

if __name__ == "__main__":
    from labrad import util
    util.runServer(LabJackServer())