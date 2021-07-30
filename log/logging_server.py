"""
Logs messages received from other LabRAD nodes. Also the wavemeter, for some reason.

..
    ### BEGIN NODE INFO
    [info]
    name = logging
    version = 1
    description = server for logging
    instancename = %LABRADNODE%_logging
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
import labrad

from pathlib import Path
sys.path.append([str(i) for i in Path(__file__).parents if str(i).endswith("labrad_tools")][0])
from client_tools.connection import connection

from twisted.internet.defer import inlineCallbacks, returnValue, Deferred
from twisted.internet import reactor
from twisted.internet.task import LoopingCall
from datetime import datetime
import io
import os, errno
import json

BETWEEN_SHOTS_TIME = 10 # how often to log the wavemeter between shots (s)
DURING_SHOT_TIME = 0.1 # how often to log the wavemeter during a shot (s)

PATHBASE = 'K:/data/'

class LoggingServer(LabradServer):
    """Logs messages received from other LabRAD nodes"""
    name = '%LABRADNODE%_logging'

    def __init__(self):
        self.name = '{}_logging'.format(getNodeName())
        self.shot = -1
        self.next_shot = 0
        self.last_time = datetime.now()
        self.logfile = None
        self.freqfile = None
        self.path = None
        LabradServer.__init__(self)
        self.set_save_location()
        self.opentime = datetime.now()

    @inlineCallbacks
    def initServer(self):
        self.wavemeter = yield self.client.servers['wavemeterlaptop_wavemeter']
        self.wavemetercall = LoopingCall(self.log_frequency)
        self.wavemetercall.start(BETWEEN_SHOTS_TIME, now=False)

        try:
            self.labjack = yield self.client.servers['polarkrb_labjack']
        except Exception as e:
            self.labjack = None
            print("Could not connect to LabJack:")
            print(e)

    @setting(1, message='s', time='t')
    def log(self, c, message, time=None):
        """
        log(self, c, message, time=None)
        
        Saves a timestamped message to the log file. The name of the sender is also recorded (so the client needs to call :meth:`set_name` first!).

        Args:
            c: A LabRAD context
            message (string): The message to record
            time (datetime.datetime, optional): The time to record. Defaults to None, in which case the current time is used.
        """
        if time is None:
            time = datetime.now()
        if(self.shot is None and self.opentime.date() != time.date()):
            self.set_save_location()
        logmessage = "%s - %s: %s\n" % (time.strftime('%Y-%m-%d %H:%M:%S.%f'), c["name"], message)
        print(logmessage)
        self.logfile.write(logmessage)
        self.logfile.flush()

    @setting(2, shot='i')
    def set_shot(self, c, shot=None):
        """
        set_shot(self, c, shot=None)

        Sets the number of the shot to record, which determines the folder in which data is saved. The shot number is reset daily. If the shot number is `None`, the experiment is considered idle. This means files are stored in the day's folder on the dataserver. The wavemeter is also set to log at a lower rate when the experiment is idle.

        Args:
            c: A LabRAD context (not used)
            shot (int, optional): The number of the shot to record. Defaults to None, which sets the program to log the idle experiment.
        """
        self.shot = shot
        self.set_save_location()
        try:
            self.labjack.set_shot(self.ljpath, self.shot == None)
            print("Starting labjack at path %s" % (self.ljpath))
        except Exception as e:
            print("Could not start LabJack: %s" % (e))
        try:
            self.wavemetercall.stop()
        except Exception as e:
            print("Could not stop looping call for wavemeter: %s" % (e))
        try:
            if shot is None:
                self.wavemetercall.start(BETWEEN_SHOTS_TIME)
            else:
                self.wavemetercall.start(DURING_SHOT_TIME)
        except Exception as e:
            print("Could not start looping call for wavemeter: %s" % (e))

    @setting(3, returns='i')
    def get_next_shot(self, c):
        """
        get_next_shot(self, c)
        
        Determines the number for the next shot based on the highest numbered directory in the current day's dataserver folder.

        Args:
            c: A LabRAD context (not used)

        Returns:
            int: the number for the next shot
        """
        currtime = datetime.now()

        if currtime.date() != self.last_time.date():
            self.next_shot = 0
        else:
            self.path = PATHBASE + "%s/shots/" % (currtime.strftime('%Y/%m/%Y%m%d'))
            dirlist = []
            for d in os.listdir(self.path):
                try:
                    dirlist.append(int(d))
                except:
                    dirlist.append(-1)
            self.next_shot = max(dirlist) + 1
        self.last_time = currtime

        return self.next_shot

    @setting(4, name='s')
    def set_name(self, c, name):
        """
        set_name(self, c, name)
        
        Sets the name of the client's connection. The name is entered in the log when messages are sent, so this function must be called before :meth:`log` is run.

        Args:
            c: A LabRAD context
            name (string): The name of the client's connection
        """
        print("Setting name of client %d to %s" % (c.ID[0], name))
        c["name"] = name

    @setting(5, returns='s')
    def get_path(self, c, name):
        """
        get_path(self, c)
        
        Returns the path where the current shot's data is saved.

        Args:
            c: A LabRAD context
        """
        return self.path

    @setting(6, returns='i')
    def get_shot(self, c, name):
        """
        get_path(self, c)
        
        Returns the current shot. If the current shot is None, return -1.

        Args:
            c: A LabRAD context
        """
        if self.shot is not None:
            return self.shot
        else:
            return -1

    def set_save_location(self):
        """
        Sets the save location based on the current time and shot number.
        """
        now = datetime.now()
        self.opentime = now
        if isinstance(self.logfile, io.IOBase) and not self.logfile.closed:
            self.logfile.close()
        if isinstance(self.freqfile, io.IOBase) and not self.freqfile.closed:
            self.freqfile.close()
        if self.shot is None:
            # save to a log file in the directory on the data server defined by the date; make directories if necessary
            self.path = PATHBASE + "%s/" % (now.strftime('%Y/%m/%Y%m%d'))
            self.ljpath = self.path + "labjack/"
        else:
            # save to a log file in a directory defined by the date and the shot number; make directories if necessary
            self.path = PATHBASE + "%s/shots/%d/" % (now.strftime('%Y/%m/%Y%m%d'), self.shot)
            self.ljpath = self.path
        fname = self.path+"log.txt"
        ffname = self.path+"freqs.txt"

        try:
            os.makedirs(self.path)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise
        try:
            os.makedirs(self.ljpath)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise
        self.logfile = open(fname, 'a+')
        self.freqfile = open(ffname, 'a+')
        print("Opening log file %s" % (fname))

    @inlineCallbacks
    def log_frequency(self):
        """
        log_frequency(self)

        Records the current wavemeter frequencies (and the frequency for the K trap lock in the last column.)
        """
        d = yield self.wavemeter.get_wavelengths()
        if len(d) > 0:
            data = json.loads(json.loads(d))
            freqs = [299792.458/float(i) if i > 0 else 0 for i in data["wavelengths"]]
            freqs.append(data["freq"])
            time = datetime.strptime(data["time"], "%m/%d/%Y, %H:%M:%S.%f")
            if(self.shot is None and self.opentime.date() != time.date()):
                self.set_save_location()
            logmessage = "%s: %s\n" % (time.strftime('%Y-%m-%d %H:%M:%S.%f'), str(freqs).strip('[]'))
            self.freqfile.write(logmessage)
            self.freqfile.flush()
        else:
            print("No response received from wavemeter!")

if __name__ == '__main__':
    from labrad import util
    util.runServer(LoggingServer())
    