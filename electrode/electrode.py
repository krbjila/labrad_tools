"""
### BEGIN NODE INFO
[info]
name = electrode
version = 1.0
description = 
instancename = electrode

[startup]
cmdline = %PYTHON% %FILE%
timeout = 20

[shutdown]
message = 987654321
timeout = 20
### END NODE INFO
"""
import json
import numpy as np
import sys

import subprocess
import pty
from time import sleep
import requests

import os
from datetime import datetime
from copy import deepcopy

from labrad.server import LabradServer, setting, Signal
from twisted.internet.defer import inlineCallbacks, returnValue

sys.path.append('../')
from server_tools.device_server import DeviceServer

sys.path.append('./clients/lib/')
from helpers import json_load_byteified, json_loads_byteified

from calibrations import *

PRESETS_PATH = 'values.json'
BACKUP_PATH = '/dataserver/data/'

class ElectrodeServer(LabradServer):
    name = 'electrode'
    relative_presets_path = PRESETS_PATH
    relative_backup_path = BACKUP_PATH
    
    presets_changed = Signal(101010, 'signal: presets changed', 'b')
    
    verbose = False
	server_address = "http://0.0.0.0:8000/"

    def __init__(self, config_path='./config.json'):
        super(ElectrodeServer, self).__init__()
        self.presets = []
        self.lookup = {}
        self.load_config(config_path)
        self._reload_presets()
        self.start_webserver()

    def load_config(self, path=None):
        """ set instance attributes defined in json config """
        if path is not None:
            self.config_path = path
        with open(self.config_path, 'r') as infile:
            config = json.load(infile)
            for key, value in config.items():
                setattr(self, key, value)

    def start_webserver(self):
        """
        start_webserver(self)

        Starts the electrode calculator web server.
        """
        try:
            dirname = os.path.dirname(__file__)
            master, slave = pty.openpty()
            if sys.platform == 'win32':
                cmd=os.path.abspath("../webservers/ElectrodeCalculator/bin/server.bat")
            else:
                cmd = os.path.abspath("../webservers/ElectrodeCalculator/bin/server")
            self.webserver = subprocess.Popen(
                cmd,
                cwd=os.path.abspath("../webservers/ElectrodeCalculator"),
                stdin=slave
            )
            print("Web server started!")
        except Exception as e:
            print("Could not start web server: {}".format(e))

    def stop_webserver(self):
        """
        stop_webserver(self)

        Stops the electrode calculator web server.
        """
        try:
            self.webserver.kill()
            while self.webserver.poll == None:
                sleep(0.1)
            print("Web server closed.")
        except Exception as e:
            print("Could not kill web server: {}".format(e))

    def stopServer(self):
        """
        stopServer(self)

        Called when the server is stopped. Shuts down the electrode calculator web server.
        """
        self.stop_webserver()

    @setting(1, returns='s')
    def get_presets(self, c):
        if len(self.presets) == 0:
            self._reload_presets()
        return json.dumps(self.presets)

    @setting(2, data='s')
    def update_presets(self, c, data):
        # Make into dict
        d = json_loads_byteified(data)
        
        if d != self.presets:
            # Clear dict
            self.lookup = {}
            for x in d:
                self.lookup[x['id']] = x
    
            self.presets = [self.lookup[key] for key in sorted(self.lookup.keys())]
    
            with open(self.relative_presets_path, 'w') as f:
                f.write(json.dumps(self.presets, sort_keys=True, indent=4))
            self.backup_presets()
    
            if self.verbose:
                print("Settings update and back up:")
                for x in self.presets:
                    print("{}: {}".format(int(x['id']), x['description']))
    
            self.presets_changed(False)


    # Only update keys that are currently in the presets dict
    @setting(5, data='s', returns='i')
    def soft_update(self, c, data):
        # Make into dict
        try:
            d = json_loads_byteified(data)
        except:
            return -1
        
        temp = deepcopy(self.lookup)
        
        for k, v in d.items():
            if self.lookup.has_key(k):
                if v != self.lookup[k]:
                    self.lookup[k] = v
        
        if self.lookup != temp:
            self.presets = [self.lookup[key] for key in sorted(self.lookup.keys())]
        
            with open(self.relative_presets_path, 'w') as f:
                f.write(json.dumps(self.presets, sort_keys=True, indent=4))
            self.backup_presets()
        
            if self.verbose:
                print("Settings soft update and back up:")
                for x in self.presets:
                    print("{}: {}".format(int(x['id']), x['description']))
            self.presets_changed(True)
        return 0


    def backup_presets(self):
        folder_s = datetime.now().strftime("%Y/%m/%Y%m%d/electrode/")
        file_s = datetime.now().strftime("%H%M%S.json")
    
        backup_folder = self.relative_backup_path + folder_s
        backup_file = backup_folder + file_s
    
        if not os.path.exists(backup_folder):
            os.mkdir(backup_folder)
    
        with open(backup_file, 'w') as f:
            f.write(json.dumps(self.presets, sort_keys=True, indent=4))
    
        print("Settings backed up at {}".format(backup_file))

    @setting(3)
    def reload_presets(self, c):
        self._reload_presets()
    
        if self.verbose:
            print("Settings reloaded:")
            for x in self.presets:
                print("{}: {}".format(int(x['id']), x['description']))
        self.presets_changed(False)

    def _reload_presets(self):
        if os.path.exists(self.relative_presets_path):
            with open(self.relative_presets_path, 'r') as f:
                presets = json_load_byteified(f)
        else:
            presets = [
                {'id': str(0), 'values': ZEROS, 'compShim': 0., 'description': 'Zero'}
            ]
            with open(self.relative_presets_path, 'w') as f:
                f.write(json.dumps(presets, sort_keys=True, indent=4))
    
           for x in presets:
            self.lookup[x['id']] = x
        self.presets = [self.lookup[key] for key in sorted(self.lookup.keys())]

    @setting(4, returns='s')
    def get_channels(self, c):
        return json.dumps(self.channels)

    @setting(6, flag='b', returns='s')
    def set_verbose(self, c, flag):
        if flag:
            self.verbose = True
            return "Verbose setting on."
        else:
            self.verbose = False
            return "Verbose setting off."

	#TODO: Finish implementing this
	@setting(7, voltages='s', returns='s')
	def get_params(self, c, voltages)
		req = requests.post(server_address+"/params", voltages)
		return req.text

	#TODO: Finish implementing this
	@setting(8, message='s', returns='s')
	def get_ramps(self, c, start, end)
		req = requests.post(server_address+"/opt", messge)
		return req.text

    
if __name__ == "__main__":
    from labrad import util
    util.runServer(ElectrodeServer())
