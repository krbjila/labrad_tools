"""
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
import labrad
sys.path.append("../client_tools")
from connection import connection
from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.internet import reactor
from twisted.internet.task import LoopingCall
from datetime import datetime
import io
import os, errno
import json

BETWEEN_SHOTS_TIME = 10 # how often to log the wavemeter between shots (s)
DURING_SHOT_TIME = 0.1 # how often to log the wavemeter during a shot (s)

class LoggingServer(LabradServer):
    """Logs messages received from other LabRAD nodes"""
    name = '%LABRADNODE%_logging'

    def __init__(self):
        self.name = 'imaging_logging'
        self.shot = None
        self.logfile = None
        self.freqfile = None
        super(LoggingServer, self).__init__()
        self.set_save_location()
        self.connect()
        self.opentime = datetime.now()

        self.wavemetercall = LoopingCall(self.log_frequency)
        self.wavemetercall.start(BETWEEN_SHOTS_TIME, now=False)

    @inlineCallbacks
    def connect(self):
        self.cxn = connection()
        yield self.cxn.connect()
        self.wavemeter = yield self.cxn.get_server('wavemeterlaptop_wavemeter')

    @setting(1, message='s', time='t')
    def log(self, c, message, time=None):
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
        self.shot = shot
        self.set_save_location()
        self.wavemetercall.stop()
        if shot is None:
            self.wavemetercall.start(BETWEEN_SHOTS_TIME)
        else:
            self.wavemetercall.start(DURING_SHOT_TIME)

    @setting(3, name='s')
    def set_name(self, c, name):
        print("Setting name of client %d to %s" % (c.ID[0], name))
        c["name"] = name

    def set_save_location(self):
        now = datetime.now()
        self.opentime = now
        if isinstance(self.logfile, io.IOBase) and not self.logfile.closed:
            self.logfile.close()
        if isinstance(self.freqfile, io.IOBase) and not self.freqfile.closed:
            self.freqfile.close()
        if self.shot is None:
            # save to a log file in the directory on the data server defined by the date; make directories if necessary
            path = "K:/data/%s/" % (now.strftime('%Y/%m/%Y%m%d'))
        else:
            # save to a log file in a directory defined by the date and the shot number; make directories if necessary
            path = "K:/data/%s/shots/%d/" % (now.strftime('%Y/%m/%Y%m%d'), self.shot)
        fname = path+"log.txt"
        ffname = path+"freqs.txt"

        try:
            os.makedirs(path)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise
        self.logfile = open(fname, 'a+')
        self.freqfile = open(ffname, 'a+')
        print("Opening log file %s" % (fname))

    @inlineCallbacks
    def log_frequency(self):
        d = yield self.wavemeter.get_wavelengths()
        data = json.loads(json.loads(d))
        freqs = [299792.458/float(i) for i in data["wavelengths"]]
        time = datetime.strptime(data["time"], "%m/%d/%Y, %H:%M:%S.%f")
        if(self.shot is None and self.opentime.date() != time.date()):
            self.set_save_location()
        logmessage = "%s: %s\n" % (time.strftime('%Y-%m-%d %H:%M:%S.%f'), str(freqs).strip('[]'))
        self.freqfile.write(logmessage)
        self.freqfile.flush()

if __name__ == '__main__':
    from labrad import util
    util.runServer(LoggingServer())
