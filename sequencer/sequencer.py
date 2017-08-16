"""
### BEGIN NODE INFO
[info]
name = sequencer
version = 1.0
description = 
instancename = sequencer

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

from labrad.server import setting, Signal
from twisted.internet.defer import inlineCallbacks, returnValue

sys.path.append('../')
from server_tools.device_server import DeviceServer

UPDATE_ID = 698032
TRIGGER_CHANNEL = 'Trigger@D15'

class SequencerServer(DeviceServer):
    #update = Signal(UPDATE_ID, 'signal: update', 's')
    update = Signal(UPDATE_ID, 'signal: update', 'b')
    name = 'sequencer'
    
    def id2channel(self, channel_id):
        """
        expect 3 possibilities for channel_id.
        1) name -> return channel with that name
        2) @loc -> return channel at that location
        3) name@loc -> first try name, then location
        """
        channel = None
        nameloc = channel_id.split('@') + ['']
        name = nameloc[0]
        loc = nameloc[1]
#        try:
#            name, loc = channel_id.split('@')
#        except:
#            name = channel_id
#            loc = None

        if name:
            for d in self.devices.values():
                for c in d.channels:
                    if c.name == name:
                        channel = c
        if not channel:
            for d in self.devices.values():
                for c in d.channels:
                    if c.loc == loc:
                        channel = c

        if channel is None:
            message = 'could not find channel based on ID {}.'.format(channel_id)
            raise Exception(message)
        return channel

    @setting(10)
    def get_channels(self, cntx):
        channels = {c.key: c.__dict__
                for d in self.devices.values() 
                for c in d.channels}
        return json.dumps(channels, default=lambda x: None)
    
    @setting(11, sequence='s')
    def run_sequence(self, c, sequence):
        fixed_sequence = self._fix_sequence_keys(json.loads(sequence))
        for device in self.devices.values():
            yield device.program_sequence(fixed_sequence)
        for device in self.devices.values():
            if device.sequencer_type == 'analog':
                yield device.start_sequence()

#		# removed KM 08/11/2017
#		# we need to take care to start KRbDigi02 before KRbDigi01
#		# else there's no time for Digi02 to get set up before being triggered
#		# and see ~2 ms timing jitter between the boards      
#		for device in self.devices.values():
#			if device.sequencer_type == 'digital':
#				yield device.start_sequence()

         # start KRbDigi02 before KRbDigi01
        for device in self.devices.values():
            if device.address != 'KRbDigi01' and device.sequencer_type == 'digital':
                yield device.start_sequence()
        for device in self.devices.values():
            if device.address == 'KRbDigi01':
                yield device.start_sequence()

    @setting(12, channel_id='s', mode='s')
    def channel_mode(self, c, channel_id, mode=None):
        channel = self.id2channel(channel_id)
        if mode is not None:
            yield channel.set_mode(mode)
        yield self.send_update(c)
        returnValue(channel.mode)
    
    @setting(13, channel_id='s', output='?')
    def channel_manual_output(self, c, channel_id, output=None):
        channel = self.id2channel(channel_id)
        if output is not None:
            yield channel.set_manual_output(output)
        yield self.send_update(c)
        returnValue(channel.manual_output)

    @setting(14, sequence='s', returns='s')
    def fix_sequence_keys(self, c, sequence):
        sequence = json.loads(sequence)
        sequence_keyfix = self._fix_sequence_keys(sequence)
        return json.dumps(sequence_keyfix)
    
    @setting(15, sequencer='s', returns='s')
    def sequencer_mode(self, c, sequencer):
        return self.devices[sequencer].mode
    
    def _fix_sequence_keys(self, sequence):
        # take sequence name@loc to configuration name@loc
#        locs = [key.split('@')[1] for key in sequence.keys()]
#        for key in sequence.keys():
#            name, loc = key.split('@')
#            for d in self.devices.values():
#                for c in d.channels:
#                    if c.loc == loc:
#                        s = sequence.pop(key)
#                        sequence.update({c.key: s})
#                    elif c.loc not in locs:
#                        sequence.update({c.key: [
#                            {'dt': dt, 'out': c.manual_output}
#                                for dt in sequence[TRIGGER_CHANNEL]]})
#        return sequence
        fixed_sequence = {}
        for old_id, channel_sequence in sequence.items():
            channel = self.id2channel(old_id)
            fixed_sequence[channel.key] = channel_sequence

        # make sure every channel has defined sequence
        for d in self.devices.values():
            for c in d.channels:
                if c.key not in fixed_sequence:
                    default_sequence = [{'dt': s['dt'], 'out': c.manual_output} 
                                        for s in sequence[TRIGGER_CHANNEL]]
                    fixed_sequence.update({c.key: default_sequence})
        return fixed_sequence
    
    @setting(2)
    def send_update(self, c):
        yield self.update(True)
    
if __name__ == "__main__":
    from labrad import util
    util.runServer(SequencerServer())
