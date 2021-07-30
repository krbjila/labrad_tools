"""
### BEGIN NODE INFO
[info]
name = dds
version = 1.1
description = 
instancename = %LABRADNODE%_dds

[startup]
cmdline = %PYTHON% %FILE%
timeout = 20

[shutdown]
message = 987654321
timeout = 20
### END NODE INFO
"""
import sys

from time import sleep

from labrad.server import LabradServer, setting, Signal
from twisted.internet.defer import inlineCallbacks, returnValue

import json

import datetime
import os

from copy import deepcopy

from pathlib import Path
sys.path.append([str(i) for i in Path(__file__).parents if str(i).endswith("labrad_tools")][0])
from server_tools.device_server import DeviceServer

class ddsServer(DeviceServer):
    """Provides access to hardware's serial interface """
    name = '%LABRADNODE%_dds'
    current_values = {}
    last_update_time = ''

    @setting(10)
    def get_channels(self, cntx):
        channels = {c.name: c.__dict__
            for d in self.devices.values() 
                for c in d.channels}
        return json.dumps(channels, default=lambda x: None)

    # Convenient way to get the channel output from iPython, etc.
    @setting(11, dev='s', board='i', channel='i', returns='s')
    def getChannel(self, c, dev, board, channel):
        
        # Try to open the device
        try:
            device = self.devices[dev]
        except:
            return "Can't find device.\n"

        # Try to get the channel
        try:
            ret = device.getChannel(board, channel)
        except:
            return "Can't find channel.\n"

        # Try to get the current value
        if ret != None:
           return "{} at {} MHz.\n".format(ret['name'], ret['frequency'])
        else:
            return "Requested channel is not initialized.\n"


    # Updating the DDS
    @setting(12, sequence='s')
    def update_dds(self, c, sequence):
        # Get the sequence
        sequence = json.loads(sequence)

        # Check whether any channels are actually changing!    
        fixed_sequence = {}
        for key, value in sequence.items():

            # If the device name ("key") is not in the self.current_values dict and
            # it refers to a real device, add it
            if key not in self.current_values and key in self.devices:
                self.current_values[key] = {}

            # If the key is valid
            if key in self.devices:
                fixed_sequence[key] = []
                channels = [c.__dict__ for c in self.devices[key].channels]
                
                # Data is coming in as
                # sequence = {device: [{"address": address, "frequency": frequency}, ...], ...}
                for entry in value:
                    # For convenience, the current values are located in a dict of format:
                    # self.current_values = {
                    #     device: {"channel_name": frequency}
                    # }
                    # So we need to get the channel names
                    for c in channels:
                        if entry['address'] == c['loc']:
                            entry['name'] = c['name']
                    try:
                        # Check if the channel name is in the dict already
                        if entry['name'] in self.current_values[key].keys():
                            # If frequency is not the same, then we add it to the list of changes
                            if entry['frequency'] != self.current_values[key][entry['name']]:
                                fixed_sequence[key].append(entry)
                        # If it's not, that's because the channel has never been updated since the server has been alive
                        # so it doesn't know what the value is
                        else:
                            fixed_sequence[key].append(entry)

                        # Set the current value in the dict to the current frequency
                        self.current_values[key][entry['name']] = entry['frequency']
                    except Exception as e:
                        print(e)


        # Expect a dict of format:
        # {"device": [{"address": address, "frequency": frequency}, ... ], ...}
        flag = 0 # Flag keeps track of whether any channels were actually updated
        for key, value in fixed_sequence.items():
            if key in self.devices and len(value) > 0:
                dev = self.devices[key]
                dev.program_frequencies(value)
                flag = 1

        # If an update occurred, need to update the backup
        if flag == 1:
            # Check directory for backup
            nowtime = datetime.datetime.now()
            # savedir = nowtime.strftime('.\\backup\\' + '%Y%m%d\\')
            savedir = nowtime.strftime('.\\backup\\')
            if not os.path.isdir(savedir):
                os.makedirs(savedir)

            self.last_update_time = nowtime.strftime('%H:%M:%S')

            # # Write the json string to the backup file
            # with open(savedir + nowtime.strftime('%H_%M_%S') + ".txt", 'w') as f:
            #     f.write(json.dumps(fixed_sequence))
            
            # Write the json string to the backup file
            with open(savedir + nowtime.strftime('%Y%m%d') + ".txt", 'a') as f:
                f.write(self.last_update_time + " :\n")
                f.write(json.dumps(fixed_sequence))
                f.write("\n")


    @setting(13, returns='s')
    def get_last_update_time(self, c):
        return self.last_update_time


__server__ = ddsServer()

if __name__ == '__main__':
    from labrad import util
    util.runServer(__server__)

