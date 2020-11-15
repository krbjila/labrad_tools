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
sys.path.append("../client_tools")
# from connection import connection
from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.internet import reactor
from datetime import datetime
import io
import os, errno

class LoggingServer(LabradServer):
    """Logs messages received from other LabRAD nodes"""
    name = '%LABRADNODE%_logging'

    def __init__(self):
        self.name = 'polarkrb_logging'
        self.shot = None
        self.logfile = None
        super(LoggingServer, self).__init__()
        self.set_save_location()

    @setting(1, message='s', time='t')
    def log(self, c, message, time=None):
        if time is None:
            time = datetime.now()
        logmessage = "%s - %s: %s\n" % (time.strftime('%Y-%m-%d %H:%M:%S.%f'), c["name"], message)
        print(logmessage)
        self.logfile.write(logmessage)
        self.logfile.flush()

    @setting(2, shot='i')
    def set_shot(self, c, shot=None):
        self.shot = shot
        self.set_save_location()

    @setting(3, name='s')
    def set_name(self, c, name):
        print("setting name of client %d to %s" % (c.ID[0], name))
        c["name"] = name

    def set_save_location(self):
        now = datetime.now()
        if isinstance(self.logfile, io.IOBase) and not self.logfile.closed:
            self.logfile.close()
        if self.shot is None:
            # save to a log file in the directory on the data server defined by the date; make directories if necessary
            path = "K:/data/%s/" % (now.strftime('%Y/%m/%Y%m%d'))
            fname = path+"log.txt"
        else:
            # save to a log file in a directory defined by the date and the shot number; make directories if necessary
            path = "K:/data/%s/shots/%d/" % (now.strftime('%Y/%m/%Y%m%d'), self.shot)
            fname = path+"log.txt"
        try:
            os.makedirs(path)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise
        self.logfile = open(fname, 'a+')
        print("Opening log file %s" % (fname))

if __name__ == '__main__':
    from labrad import util
    util.runServer(LoggingServer())