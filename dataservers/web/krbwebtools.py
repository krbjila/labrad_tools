"""
### BEGIN NODE INFO
[info]
name = krbwebtools
version = 1.0
description = 
instancename = krbwebtools

[startup]
cmdline = %PYTHON% %FILE%
timeout = 20

[shutdown]
message = 987654321
timeout = 20
### END NODE INFO
"""

from labrad.server import LabradServer, setting, Signal
from twisted.web.server import Site, NOT_DONE_YET, Session
from twisted.web.resource import Resource
from twisted.web.static import File

import django
from django.conf import settings

import json
from datetime import datetime
import os
from copy import copy, deepcopy
from itertools import chain

import sys
sys.path.append('./lib/backend/python/')
from krbtools_resources import *

class KRbWebTools(LabradServer):
    """
    Data server for compiling experimental sequences and tracking sequence versions
    """
    name = "krbwebtools"

    def __init__(self):
        super(KRbWebTools, self).__init__()

        # Configure Django for templating
        path = os.path.dirname(os.path.realpath(__file__)) + '/lib/app/templates/'
        settings.configure(
            TEMPLATES=[{
                'BACKEND': 'django.template.backends.django.DjangoTemplates',
                'DIRS': [path]
            }]
        )
        django.setup()

    def load_config(self, path=None):
        if path is not None:
            self.config_path = path
            with open(path, 'r') as f:
                config = json.load(f)
                for k,v in config.items():
                    setattr(self, k, v)

    def initServer(self):
        self.start()

    def start(self):
        root = Resource()

        self.base = KRbRoot()
        self.home = KRbHome()
        self.styles = File("./lib/app/styles")
        self.scripts = File("./lib/app/scripts")
        self.images = File("./lib/app/images")

        self.dashboard = Dashboard(self.client)
        self.running_servers = RunningServers(self.client)
        self.other = Other(self.client)

        self.visualizer = Visualizer()
        self.visualizer_load = VisualizerLoad(self.client)
        self.visualizer_show = VisualizerShow(self.client)
    
        root.putChild("krbtools", self.base)
        self.base.putChild("home", self.home)
        self.base.putChild("styles", self.styles)
        self.base.putChild("scripts", self.scripts)
        self.base.putChild("images", self.images)
        
        self.home.putChild("dashboard", self.dashboard)
        self.home.putChild("runningservers", self.running_servers)
        self.home.putChild("other", self.other)

        self.base.putChild("visualizer", self.visualizer)
        self.visualizer.putChild("load", self.visualizer_load)
        self.visualizer.putChild("show", self.visualizer_show)

        d = datetime.now()
        datestring = d.strftime("%Y%m%d_%H%M%S")
        factory = Site(root, logPath=b"./lib/backend/log/{}.log".format(datestring))
        endpoint = endpoints.TCP4ServerEndpoint(reactor, 8888)
        endpoint.listen(factory)

    def stopServer(self):
        pass

if __name__ == "__main__":
    from labrad import util
    util.runServer(KRbWebTools())
