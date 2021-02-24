"""
Provides access to LabJack T7 DAQ.

..
    ### BEGIN NODE INFO
    [info]
    name = labjack
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

        config_fname = "../log/logging_config.json"
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
        """
        Reads latest data from LabJack, computes times relative to the start of the scan, and saves data to a file.
        """
        while self.running:
            ret = ljm.eStreamRead(self.handle)
            self.skips += ret[0].count(-9999.0)
            # print("Skips: %d, Scan Backlogs: Device = %i, LJM = %i" % (self.skips, ret[1], ret[2]))
            if self.idle:
                data = np.array(ret[0], dtype=np.float64).reshape(-1, self.nchannels)[[0],:]
            else:
                data = np.array(ret[0], dtype=np.float64).reshape(-1, self.nchannels)
            data[:,2] = data[:,2]*65536+data[:,1]
            if self.start_time == -1:
                self.start_time = data[0,2]
            data[:,2] = (data[:,2] - self.start_time)
            diffs = np.diff(data[:,2], prepend = self.last_time) < 0
            self.last_time = data[-1, 2]
            data[:,2] = data[:,2] + (self.n_rollovers + diffs) * 2**32
            if np.any(diffs):
                self.n_rollovers += 1
            data[:, 2] = data[:,2] / 40E6
            np.savetxt(self.file, data[:,2:], delimiter=',',header='',comments='',fmt="%.3f,"*(self.nchannels-2))
            self.file.flush()

    @setting(3, scansPerRead='i', aScanList='*s', scanRate='v')
    def setup_stream(self, c, scansPerRead, aScanList, scanRate):
        """
        setup_stream(self, c, scansPerRead, aScanList, scanRate)
        
        Sets up and starts a LabJack stream. The stream is nonblocking, since the read function is automatically started in a new thread. The data is saved in a location set by :meth:`set_shot`

        Args:
            c: A LabRAD context (not used)
            scansPerRead (int): The number of scans to be taken before the data is read into the computer. Should typically be set so the data is read at ~1 Hz.
            aScanList (list of strings): An ordered list of the channels to be read. See `the LabJack docs <https://labjack.com/support/datasheets/t-series/communication/stream-mode#streamable-registers>`__ for a list of streamable registers.
            scanRate (int): The scan rate in Hz
        """
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
        aValues = [ljm.constants.GND, 0, 1, 32768]
        # Write the analog inputs' negative channels (when applicable), ranges,
        # stream settling time and stream resolution configuration.
        numFrames = len(aNames)
        ljm.eWriteNames(self.handle, numFrames, aNames, aValues)
        aScanList = ['FIO_STATE', 'CORE_TIMER', 'STREAM_DATA_CAPTURE_16'] + aScanList
        self.nchannels = len(aScanList)
        self.start_time = -1
        self.last_time = -np.inf
        self.n_rollovers = 0
        print("starting stream")
        ljm.eStreamStart(self.handle, scansPerRead, self.nchannels, ljm.namesToAddresses(self.nchannels, aScanList)[0], scanRate)
        self.running = True
        Thread(target = self.read).start()

    @setting(4, addr='s', returns='v')
    def read_register(self, c, addr):
        """
        read_register(self, c, addr)
        
        Reads a register on the LabJack. Returns a float, which may need to be interpreted bitwise.

        Args:
            c: A LabRAD context (not used)
            addr (string): The address of the register. See `the LabJack docs <https://labjack.com/support/datasheets/t-series/communication/modbus-map>`__ for a list of registers.

        Returns:
            float: The contents of the register. This may need to be converted to a bit string. Zero is returned if an error occurs.

        """
        try:
            returnValue(ljm.eReadName(self.handle, addr))
        except Exception as e:
            print(e)
            returnValue(0.0)
        
    @setting(5, addr='s', val='v')
    def write_register(self, c, addr, val):
        """
        write_register(self, c, addr, val)
        
        Writes to a register on the LabJack.

        Args:
            c: A LabRAD context (not used)
            addr (string): The address of the register. See `the LabJack docs <https://labjack.com/support/datasheets/t-series/communication/modbus-map>`__ for a list of registers.
            val (float): The value to be written to the register.
        """
        try:
            ljm.eWriteName(self.handle, addr, val)
        except Exception as e:
            print(e)
        
    @setting(6, addr='s', returns='s')
    def read_register_string(self, c, addr):
        """
        read_register_string(self, c, addr)
        
        Reads a register containing a string on the LabJack.

        Args:
            c: A LabRAD context (not used)
            addr (string): The address of the register. See `the LabJack docs <https://labjack.com/support/datasheets/t-series/communication/modbus-map>`_ for a list of registers.

        Returns:
            string: The contents of the register. An empty string is returned if an error occurs.

        """
        try:
            returnValue(ljm.eReadNameString(self.handle, addr))
        except Exception as e:
            print(e)
            returnValue("")

    @setting(7, addr='s', val='s')
    def write_register_string(self, c, addr, val):
        """
        write_register(self, c, addr, val)
        
        Writes to a register containing a string on the LabJack.

        Args:
            c: A LabRAD context (not used)
            addr (string): The address of the register. See `the LabJack docs <https://labjack.com/support/datasheets/t-series/communication/modbus-map>`_ for a list of registers.
            val (string): The value to be written to the register.
        """
        try:
            ljm.eWriteNameString(self.handle, addr, val)
        except Exception as e:
            print(e)

    @setting(8)
    def stop_stream(self, c):
        """
        stop_stream(self, c)

        Stops a stream, if one is running.

        Args:
            c: A LabRAD context (not used)
        """
        self.running = False
        try:
            if(ljm.eReadAddress(self.handle, 4990, 1)): #STREAM_ENABLE
                ljm.eStreamStop(self.handle)
        except Exception as e:
            print(e)

    @setting(9, path='s', idle='b')
    def set_shot(self, c, path, idle=False):
        """
        set_shot(self, c, path, idle=False)
        
        Sets the save path and logging rate for the LabJack.

        Args:
            c: A LabRAD context (not used)
            path (string): A directory that the LabJack data is saved to.
            idle (bool, optional): If True, only saves the first point from each read. If False, saves all data. Defaults to False.
        """
        if path == "":
            self.fname = os.devnull
        else:
            self.fname = path + "labjack_"+datetime.now().strftime("%Y-%m-%d_%H-%M-%S.%f")+".csv"
        self.start_time = -1
        self.n_rollovers = 0
        self.last_time = -np.inf
        print("logging scan at %s" % (self.fname))
        old_file = self.file
        new_file = open(self.fname, "a+")
        new_file.write('time,')
        [new_file.write('%s,' % str(c["name"])) for c in self.config["channels"]]
        new_file.write('\n')
        new_file.write('time,')
        [new_file.write('%s,' % str(c["id"])) for c in self.config["channels"]]
        new_file.write('\n')
        self.file = new_file
        self.idle = idle
        try:
            old_file.close()
        except:
            print("could not close file!")

    @setting(10)
    def stopServer(self):
        """
        Run when the LabRAD server is stopped. Stops any running stream, closes any open files, and closes the connection to the LabJack.
        """
        self.set_shot(None, "", idle=True)
        self.stop_stream(None)
        ljm.close(self.handle)
        

if __name__ == "__main__":
    from labrad import util
    util.runServer(LabJackServer())