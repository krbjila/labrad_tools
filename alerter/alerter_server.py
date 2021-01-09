"""
### BEGIN NODE INFO
[info]
name = alerter
version = 1
description = it can talk!
instancename = %LABRADNODE%_alerter

[startup]
cmdline = %PYTHON% %FILE%
timeout = 20

[shutdown]
message = 987654321
timeout = 20
### END NODE INFO
"""
import sys
import pyttsx3
from datetime import datetime
from labrad.server import LabradServer, setting
from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.internet.task import LoopingCall

class alerterServer(LabradServer):
    """Talks!"""
    name = '%LABRADNODE%_alerter'

    def __init__(self):
        self.USB_server_name = 'polarkrb_alerter'
        LabradServer.__init__(self)
    
    # @inlineCallbacks
    def initServer(self):
        self.engine = pyttsx3.init()
        self.engine.startLoop(False)
        l = LoopingCall(self.engine.iterate)
        l.start(0.1)


    @setting(5, message="s")
    def say(self, c, message):
        print(message)
        self.engine.say(message)

if __name__ == '__main__':
    from labrad import util
    util.runServer(alerterServer())
