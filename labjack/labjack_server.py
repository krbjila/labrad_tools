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
from threading import Thread
from labjack import ljm
import pandas as pd
import numpy as np
from datetime import datetime
import json
import os

class LabJackServer(LabradServer):
    """Provides access to LabJack T7 DAQ."""
    name = '%LABRADNODE%_labjack'

    def __init__(self):
        super(LabJackServer, self).__init__()

        config_fname = "../logging/logging_config.json"
        with open(config_fname, 'r') as f:
            self.config = json.load(f)['labjack']

        self.handle = ljm.openS("T7", "ANY", "ANY")

        info = ljm.getHandleInfo(self.handle)
        print("Opened a LabJack with Device type: %i, Connection type: %i,\n"
        "Serial number: %i, IP address: %s, Port: %i,\nMax bytes per MB: %i" %
        (info[0], info[1], info[2], ljm.numberToIP(info[3]), info[4], info[5]))

        self.running = False
        self.idle = True
        self.skips = 0
        self.scan_list = [str(c["id"]) for c in self.config["channels"]]
        self.fname = os.devnull
        self.file = open(self.fname, "a+")
        self.setup_stream(None, self.config["scansperread"], self.scan_list, self.config["scanrate"])

    
    def read(self):
        while self.running:
            ret = ljm.eStreamRead(self.handle)
            self.skips += ret[0].count(-9999.0)
            print("Skips: %d, Scan Backlogs: Device = %i, LJM = "
              "%i" % (self.skips, ret[1], ret[2]))
            if self.idle:
                data = np.array(ret[0], dtype=np.float64).reshape(-1, self.nchannels)[[0],:]
            else:
                data = np.array(ret[0], dtype=np.float64).reshape(-1, self.nchannels)
            # data[:,2] = data[:,2]*65536+data[:,1]
            # if self.start_time == -1:
            #     self.start_time = data[0,2]
            # data[:,2] = (data[:,2] - self.start_time)/40E6
            # np.savetxt(self.file, data[:,2:], delimiter=',',header='',comments='',fmt="%f,"*(self.nchannels-2))
            np.savetxt(self.file, data, delimiter=',',header='',comments='',fmt="%f,"*(self.nchannels))
            self.file.flush()

    @setting(3, scansPerRead='i', aScanList='*s', scanRate='v')
    def setup_stream(self, c, scansPerRead, aScanList, scanRate):
        if(ljm.eReadAddress(self.handle, 4990, 1)): #STREAM_ENABLE
            ljm.eStreamStop(self.handle)
        # Ensure triggered stream is disabled.
        ljm.eWriteName(self.handle, "STREAM_TRIGGER_INDEX", 0)

        # Enabling internally-clocked stream.
        ljm.eWriteName(self.handle, "STREAM_CLOCK_SOURCE", 0)

        # All negative channels are single-ended, AIN0 and AIN1 ranges are
        # +/-10 V, stream settling is 0 (default) and stream resolution index
        # is 0 (default).
        aNames = ["AIN_ALL_NEGATIVE_CH", "STREAM_SETTLING_US", "STREAM_RESOLUTION_INDEX", "STREAM_BUFFER_SIZE_BYTES"]
        aValues = [ljm.constants.GND, 0, 0, 32768]
        # Write the analog inputs' negative channels (when applicable), ranges,
        # stream settling time and stream resolution configuration.
        numFrames = len(aNames)
        ljm.eWriteNames(self.handle, numFrames, aNames, aValues)
        # aScanList = ['FIO_STATE', 'CORE_TIMER', 'STREAM_DATA_CAPTURE_16'] + aScanList
        self.nchannels = len(aScanList)
        self.start_time = -1
        print("starting stream")
        ljm.eStreamStart(self.handle, scansPerRead, self.nchannels, ljm.namesToAddresses(self.nchannels, aScanList)[0], scanRate)
        self.running = True
        Thread(target = self.read).start()

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
        self.running = False
        try:
            if(ljm.eReadAddress(self.handle, 4990, 1)): #STREAM_ENABLE
                ljm.eStreamStop(self.handle)
        except Exception as e:
            print(e)

    @setting(9, path='s', idle='b')
    def set_shot(self, c, path, idle=False):
        if path == "":
            self.fname = os.devnull
        else:
            self.fname = path + "labjack_"+datetime.now().strftime("%Y-%m-%d_%H-%M-%S.%f")+".csv"
        self.start_time = -1
        print("logging scan at %s" % (self.fname))
        old_file = self.file
        self.file = open(self.fname, "a+")
        # self.file.write('time,')
        [self.file.write('%s,' % str(c["name"])) for c in self.config["channels"]]
        self.file.write('\n')
        self.idle = idle
        try:
            old_file.close()
        except:
            print("could not close file!")
        

if __name__ == "__main__":
    from labrad import util
    util.runServer(LabJackServer())