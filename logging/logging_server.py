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
        client_id = "test" #TODO: get ID from c
        self.logfile.write("%s - %s: %s" % (client_id, time.strftime('%Y-%m-%d %H:%M:%S.%f'), message))

    @setting(2, shot='i')
    def set_shot(self, c, shot=None):
        self.shot = shot
        self.set_save_location()

    def set_save_location(self):
        now = datetime.now()
        if isinstance(self.logfile, io.IOBase) and not self.logfile.closed:
            self.logfile.close()
        if self.shot is None:
            # save to a log file in the directory on the data server defined by the date; make directories if necessary
            fname = "log_%s.csv" % (now.strftime('%m_%d_%Y'))
        else:
            # save to a log file in a directory defined by the date and the shot number; make directories if necessary
            fname = "log_%s_shot_%d.csv" % (now.strftime('%m_%d_%Y'), self.shot)
        self.logfile = open(fname, 'a+')

if __name__ == '__main__':
    from labrad import util
    util.runServer(LoggingServer())