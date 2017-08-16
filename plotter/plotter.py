"""
### BEGIN NODE INFO
[info]
name = plotter
version = 1.0
description = 
instancename = plotter

[startup]
cmdline = %PYTHON% %FILE%
timeout = 20

[shutdown]
message = 987654321
timeout = 20
### END NODE INFO
"""

import imp
import json
import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as plt
import os

from time import time

from labrad.server import LabradServer, setting, Signal
from twisted.internet.defer import inlineCallbacks
from twisted.internet.reactor import callLater
from twisted.internet.task import LoopingCall
from twisted.internet.threads import deferToThread

def save_and_close(fig):
    fig.savefig('figure.svg')
    plt.close(fig)

class PlotterServer(LabradServer):
    name = 'plotter'

    def initServer(self):
        self.data = None
        self.do_plot()

    @setting(0, json_data='s')
    def plot(self, c, json_data):
	self.data = json.loads(json_data)
	print "set data", self.data

    def do_plot(self):
        if self.data:
            data = self.data
            path = data['plotter_path']
            function_name = data['plotter_function']
            module_name = os.path.split(path)[-1].strip('.py')
            module = imp.load_source(module_name, path)
            function = getattr(module, function_name)
            try:
                d = deferToThread(function, *data['args'], **data['kwargs'])
		d.addCallback(save_and_close)	

                print "saving... {}".format(time())
            except Exception, e:
                print 'ERROR: ', e
        callLater(2, self.do_plot)
            

if __name__ == "__main__":
    from labrad import util
    server = PlotterServer()
    util.runServer(server)
