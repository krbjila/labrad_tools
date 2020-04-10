"""
### BEGIN NODE INFO
[info]
name = experimentvault
version = 1.0
description = 
instancename = experimentvault

[startup]
cmdline = %PYTHON% %FILE%
timeout = 20

[shutdown]
message = 987654321
timeout = 20
### END NODE INFO
"""

from labrad.server import LabradServer, setting, Signal
from twisted.internet.defer import inlineCallbacks, returnValue

import json
from datetime import date, timedelta
import os
from copy import copy, deepcopy
from itertools import chain

class ExperimentVault(LabradServer):
    """
    Data server for serving experiment data
    """
    name = "experimentvault"

    def __init__(self, config_path='./config.json'):
        self.load_config(config_path)
        self.electrode_parameters = {}
        self.sequencer_parameters = {}
        super(ExperimentVault, self).__init__()

    def load_config(self, path=None):
        if path is not None:
            self.config_path = path
            with open(path, 'r') as f:
                config = json.load(f)
                for k,v in config.items():
                    setattr(self, k, v)

    @inlineCallbacks
    def initServer(self):
        """ Setup Labrad connections, _refresh"""
        # Update everything
        yield self._refresh()

    def _refresh(self):
        """
        Update everything:
            List of experiments 
        """
        self.refresh_experiments()

    def refresh_experiments(self):
        # Empty self.experiments
        # Will have format: {experiment_name: {date: [versions], ...}}
        expts = {}

        for i in range(365, 0, -1):
            d = date.today() - timedelta(i)
            timestr = d.strftime(self.time_format)
            path = self.file_path.format(timestr)

            if os.path.isdir(path):
                x = [f for f in os.listdir(path) if os.path.isfile(path + f)]
                for f in x:
                    name = f.split(self.version_suffix)[0]
                    version = f.split(self.version_suffix)[-1]
                    
                    if not expts.has_key(name):
                        expts[name] = {}
                    if not expts[name].has_key(timestr):
                        expts[name][timestr] = []
                    expts[name][timestr].append(int(version))
        
        for v in expts.values():
            for kk, vv in v.items():
                v[kk] = sorted(vv)

        self.experiments = expts


    @setting(1, "Refresh", returns='i')
    def refresh(self, c):
        """
        Refresh sequence list, electrode values, sequencer parameter values

        Returns:
            0 on success
            -1 on error
        """
        try:
            yield self._refresh()
            returnValue(0)
        except Exception as e:
            print "Exception in SequenceVault.refresh: " + e
            returnValue(-1)

    @setting(2, "Get available experiments", returns='s')
    def get_available_experiments(self, c):
        """
        Get all available experiments 

        Returns:
            json.dumps'ed dict
        """
        self._refresh()
        return json.dumps(self.experiments)

    @setting(3, "Get experiment data", name='s', date='s', version='i', returns='s')
    def get_experiment_data(self, c, name, date, version=-1):
        """
        Get the experiment file data

        Inputs:
            date: str, experiment date in %Y%m%d format
            name: str, experiment shortname (e.g., "highfield")
            version: int, e.g. 9 for "highfield#9". version=-1 returns the most recent file

        Returns:
            {"experiment": experiment_file, "dates": dates):
                experiment_file: json.dumps'ed contents of experiment file
                dates: list of most_recent_date for each sequence
        """
        try:
            if version == -1:
                version = self.experiments[name][date][-1]
            
            path = self.file_path.format(date)
            path += name + self.version_suffix + str(version)
            
            with open(path, 'r') as f:
                data = json.load(f)
            
            sequence_list = data['sequencer']['sequence'][0]
            sequence_vault = yield self.client.servers['sequencevault']
            dates = yield sequence_vault.get_versions_snapshot(sequence_list, date)
            returnValue(json.dumps({"experiment": data, "dates": dates}))
        except Exception as e:
            print e
            print "Exception in ExperimentVault.get_experiment_data: " + e 
            returnValue("")

if __name__ == "__main__":
    from labrad import util
    util.runServer(ExperimentVault())
