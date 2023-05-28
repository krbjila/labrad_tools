"""
Keeps track of electrode presets; communicates with control GUI and sequencer.

..
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

import os
from datetime import datetime

from labrad.server import LabradServer, setting, Signal
from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.internet.task import LoopingCall

sys.path.append('../')
from server_tools.device_server import DeviceServer

sys.path.append('./clients/lib/')
from helpers import json_load_byteified, json_loads_byteified

from calibrations import *

PRESETS_PATH = 'values.json'
BACKUP_PATH = '/dataserver/data/'

class ElectrodeServer(LabradServer):
    """
    Server for keeping track of electrode presets.
    
    Loads preset values from ``PRESETS_PATH`` (currently ``value.json``) when started and saves backup files to ``BACKUP_PATH`` (currently ``/dataserver/data/``).

    Electrode presets are stored in JSON files, with a typical entry being of the form

    .. code-block:: json
    
        {
        "compShim": 0.0, 
        "description": "Zero", 
        "id": 0, 
        "normalModes": {
            "Bias": 0.0, 
            "CompShim": 0.0, 
            "EastWest": 0.0, 
            "GlobalOffset": 0.0, 
            "HGrad": 0.0, 
            "RodOffset": 0.0, 
            "RodScale": 0.0
        }, 
        "values": {
            "LE": -0.00017701416113289064, 
            "LP": -0.0002633327836823617, 
            "LW": -0.00021936947516227844, 
            "UE": -0.00018548979806110665, 
            "UP": -0.00024036059085730274, 
            "UW": -0.0002263664437981591
        }, 
        "volts": {
            "LE": 0.0, 
            "LP": 0.0, 
            "LW": 0.0, 
            "UE": 0.0, 
            "UP": 0.0, 
            "UW": 0.0
        }

    """
    
    name = 'electrode'
    relative_presets_path = PRESETS_PATH
    relative_backup_path = BACKUP_PATH
    
    presets_changed = Signal(101010, 'signal: presets changed', 'b')
    
    verbose = False

    def __init__(self, config_path='./config.json'):
        super(ElectrodeServer, self).__init__()
        self.presets = []
        self.lookup = {}
        self.load_config(config_path)
        self._reload_presets()
        self.time = None

        try:
            subprocess.check_output("curl http://127.0.0.1:8000/", shell=True)
        except:
            self.start_webserver()
        
        l = LoopingCall(self.daily_backup)
        l.start(60)

    def daily_backup(self):
        """
        daily_backup(self)

        Called every minute. Checks whether presets have been backed up on the current datetime. If not, calls :meth:`backup_presets`.
        """
        if self.time is None or self.time.date() != datetime.today().date():
            self.backup_presets()
            self.time = datetime.now()


    def load_config(self, path=None):
        """
        load_config(self, path=None)
        
        Set instance attributes defined in ``config.json``.
        """
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
            primary, secondary = pty.openpty()
            if sys.platform == 'win32':
                cmd=os.path.abspath("../webservers/ElectrodeCalculator/bin/server.bat")
            else:
                cmd = os.path.abspath("../webservers/ElectrodeCalculator/bin/server")
            self.webserver = subprocess.Popen(
                cmd,
                cwd=os.path.abspath("../webservers/ElectrodeCalculator"),
                stdin=secondary
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
        """
        get_presets(self, c)

        Returns a JSON-dumped string of the presets dictionary.

        Args:
            c: LabRAD context

        Returns:
            str: A JSON-dumped string of the presets dictionary
        """
        if len(self.presets) == 0:
            self._reload_presets()
        return json.dumps(self.presets)

    @setting(2, data='s')
    def update_presets(self, c, data):
        """
        update_presets(self, c, data)

        Updates the presets dictionary with the values in the JSON-formatted string ``data``. If any of the presets have changed, save a backup file.

        Args:
            c: LabRAD context
            data (str): A JSON-formatted string of the presets
        """
        
        # Make into dict
        d = json_loads_byteified(data)
        
        if d != self.presets:
            # Clear dict
            self.lookup = {}
            for x in d:
                self.lookup[x['id']] = x
    
            self.presets = [self.lookup[key] for key in sorted(self.lookup.keys())]

            # Make sure the normalModes and main compShim values are consistent
            for preset in self.presets:
                if "normalModes" in preset and "CompShim" in preset["normalModes"]:
                    preset["compShim"] = preset["normalModes"]["CompShim"]
    
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
        """
        soft_update(self, c, data)

        Like :meth:`update_presets`, but only updates keys that are currently in the presets dictionary.

        Args:
            c: LabRAD context
            data (str): A JSON-formatted string of the presets

        Returns:
            int: 0 if succesful, -1 if data couldn't be loaded
        """
        # Make into dict
        try:
            d = json_loads_byteified(data)
        except:
            return -1
        
        changed = False
        for k, v in d.items():
            k = int(k)
            if self.lookup.has_key(k):
                electrode_setting = self.lookup[k]

                for kk, vv in v.items():
                    if kk in electrode_setting and vv != electrode_setting[kk]:
                        electrode_setting[kk] = vv
                        changed = True
        
        if changed:
            self.presets = [self.lookup[key] for key in sorted(self.lookup.keys())]

            # Make sure the normalModes and main compShim values are consistent
            for preset in self.presets:
                if "normalModes" in preset and "CompShim" in preset["normalModes"]:
                    preset["compShim"] = preset["normalModes"]["CompShim"]
        
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
        """
        backup_presets(self)

        Save a JSON-formatted backup of the presets, to a file in the ``electrode`` folder of the current day's dataserver directory. The file name is the time, formatted as ``%H%M%S.json``.
        """
        try:
            folder_s = datetime.now().strftime("%Y/%m/%Y%m%d/electrode/")
            file_s = datetime.now().strftime("%H%M%S.json")
        
            backup_folder = self.relative_backup_path + folder_s
            backup_file = backup_folder + file_s
        
            if not os.path.exists(backup_folder):
                os.mkdir(backup_folder)
        
            with open(backup_file, 'w') as f:
                f.write(json.dumps(self.presets, sort_keys=True, indent=4))
        
            print("Settings backed up at {}".format(backup_file))
        except Exception as e:
            print(e)

    @setting(3)
    def reload_presets(self, c):
        """
        reload_presets(self, c)

        Reloads presets from ``PRESETS_PATH``. If the presets file is not found, create one, with only the zero field preset.

        Args:
            c: LabRAD context
        """
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
        """
        get_channels(self, c)

        Args:
            c: LabRAD context

        Returns:
            str: A JSON-formatted string of the channel locations, as set in ``config.json``.
        """
        return json.dumps(self.channels)

    @setting(6, flag='b', returns='s')
    def set_verbose(self, c, flag):
        """
        set_verbose(self, c, flag)

        Args:
            c: LabRAD context
            flag (bool): Whether to print verbose output.

        Returns:
            str: "Verbose setting on." or "Verbose setting off."
        """
        if flag:
            self.verbose = True
            return "Verbose setting on."
        else:
            self.verbose = False
            return "Verbose setting off."

    
if __name__ == "__main__":
    from labrad import util
    util.runServer(ElectrodeServer())
