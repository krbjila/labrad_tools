"""
Allows the computer to talk using `pyttsx3 <https://pypi.org/project/pyttsx3/>`_ text to speech
"""

r"""
    ### BEGIN NODE INFO
    [info]
    name = alerter
    version = 1
    description = it can talk!
    instancename = %LABRADNODE%_alerter

    [startup]
    cmdline = "C:\\Users\\polarkrb2\\.conda\\envs\\labrad-py310\\python.exe" "%FILE%"
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
        LabradServer.__init__(self)
    
    def initServer(self):
        self.engine = pyttsx3.init()
        self.engine.startLoop(False)
        l = LoopingCall(self.engine.iterate)
        l.start(0.1)


    @setting(5, message="s")
    def say(self, c, message):
        """Makes the computer say a message with text to speech

        Args:
            c: A LabRAD context (not used)
            message (string): The message to say
        """
        print(message)
        self.engine.say(message)

if __name__ == '__main__':
    from labrad import util
    util.runServer(alerterServer())
