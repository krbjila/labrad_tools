"""
Generates and runs sequences of outputs for TTLs, DACs, and electrode DACs.

..
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

from time import sleep

UPDATE_ID = 698032
TRIGGER_CHANNEL = 'Trigger@D15'

class SequencerServer(DeviceServer):
    """
    Generates and runs sequences of outputs for TTLs, DACs, and electrode DACs.

    Connects to sequencer devices (TODO: Fancy link), as listed in `config.json <https://github.com/krbjila/labrad_tools/blob/master/sequencer/config.json>`_.

    TODO: Finish documenting all the methods.
    """
    update = Signal(UPDATE_ID, 'signal: update', 'b')
    name = 'sequencer'
    
    def id2channel(self, channel_id):
        """
        id2channel(self, channel_id)

        Returns channel corresponding to ``channel_id``. Expects 3 possibilities for ``channel_id``:

            * ``name`` -> return channel with that name
            * ``@loc`` -> return channel at that location
            * ``name@loc`` -> first try name, then location

        Args:
            channel_id (str): The identifier of the channel, as described above.

        Returns:
            The channel corresponding to ``channel_id``

        Raises:
            ``KeyError`` if channel cannot be found
        """
        channel = None
        nameloc = channel_id.split('@') + ['']
        name = nameloc[0]
        loc = nameloc[1]

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
            message = 'Could not find channel based on ID {}.'.format(channel_id)
            raise KeyError(message)
        return channel

    @setting(10)
    def get_channels(self, cntx):
        """
        get_channels(self, cntx)

        Returns a JSON-dumped dictionary of all channels on all sequencer devices.

        Args:
            cntx: The LabRAD context

        Returns:
            str: A JSON-dumped string of a dictionary, where the keys are channel names and the values are the channels.
        """
        channels = {c.key: c.__dict__
                for d in self.devices.values() 
                for c in d.channels}
        return json.dumps(channels, default=lambda x: None)
    
    @setting(11, sequence='s')
    def run_sequence(self, c, sequence):
        """
        run_sequence(self, c, sequence)

        Runs the provided sequence, first ensuring that each channel has a valid sequence, then programming each device, then starting them.

        First starts the AD5791 (TODO: fancy link) boards (stable DACs for electric field), then the analog (TODO: fancy link) boards, then finally the digital (TODO: fancy link) boards, starting ``KRbDigi01``, which triggers the others, last. If a new board is added with a difference ``sequencer_type``, it will be started along with the digital boards.

        Args:
            c: The LabRAD context
            sequence (str): A JSON-dumped string containing the sequence (TODO: Add an example of a sequence.)
        """
        fixed_sequence = self._fix_sequence_keys(json.loads(sequence))
        for device in self.devices.values():
            yield device.program_sequence(fixed_sequence)

        for device in self.devices.values():
            if device.sequencer_type == 'ad5791':
                yield device.start_sequence()

        for device in self.devices.values():
            if device.sequencer_type == 'analog':
                yield device.start_sequence()

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
        fixed_sequence = {}
        for old_id, channel_sequence in sequence.items():
            channel = self.id2channel(old_id)
            fixed_sequence[channel.key] = channel_sequence

        # make sure every channel has defined sequence
        for d in self.devices.values():
            for c in d.channels:
                if c.key not in fixed_sequence:
                    default_sequence = [{'dt': s['dt'], 'out': c.manual_output} for s in sequence[TRIGGER_CHANNEL]]
                    fixed_sequence.update({c.key: default_sequence})
        return fixed_sequence

    @setting(2)
    def send_update(self, c):
        yield self.update(True)
    
if __name__ == "__main__":
    from labrad import util
    util.runServer(SequencerServer())
