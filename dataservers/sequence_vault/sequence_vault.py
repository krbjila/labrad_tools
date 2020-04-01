"""
### BEGIN NODE INFO
[info]
name = SequenceVault
version = 1.0
description = 
instancename SequenceVault

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

class SequenceVault(LabradServer):
    """
    Data server for compiling experimental sequences and tracking sequence versions
    """
    name = "SequenceVault"

    def __init__(self, config_path='./config.json'):
        self.load_config(config_path)
        self.electrode_parameters = {}
        self.sequencer_parameters = {}
        super(SequenceVault, self).__init__()

    def load_config(self, path=None):
        if path is not None:
            self.config_path = path
            with open(path, 'r') as f:
                config = json.load(f)
                for k,v in config.items():
                    setattr(self, k, v)

    @inlineCallbacks
    def initServer(self):
        self.electrode_server = self.client.servers[self.electrode_servername]
        self.sequencer_server = self.client.servers[self.sequencer_servername]
        self.conductor_server = self.client.servers[self.conductor_servername]

        self.electrode_server.signal__presets_changed(self.electrode_presets_changed_id)
        self.electrode_server.addListener(listener=self.refresh_electrode_parameters,
                                            source=None, ID=self.electrode_presets_changed_id)

        self.conductor_server.signal__parameters_updated(self.conductor_parameters_updated_id)
        self.conductor_server.addListener(listener=self.refresh_sequencer_parameters,
                                            source=None, ID=self.conductor_parameters_updated_id)
        yield self._refresh()

    @inlineCallbacks
    def _refresh(self):
        self.refresh_sequences()
        yield self.refresh_electrode_parameters()
        yield self.refresh_sequencer_parameters()

    def refresh_sequences(self):
        self.sequences = {}

        for i in range(365,0,-1):
            d = date.today() - timedelta(i)
            timestr = d.strftime(self.time_format)
            path = self.sequence_path.format(timestr)

            if os.path.isdir(path):
                sequences = os.listdir(path)

                for name in sequences:
                    (fname, version) = self.split_filename(name)
                    if not fname in self.sequences:
                        self.sequences[fname] = {}
                    if not timestr in self.sequences[fname]:
                        self.sequences[fname][timestr] = []
                    self.sequences[name][timestr].append(version)

    @inlineCallbacks
    def refresh_electrode_parameters(self, c=None, signal=None):
        yield self.get_e_presets()
        yield self.get_e_channels()
        
    @inlineCallbacks
    def get_e_presets(self):
        self.electrode_parameters['presets'] = {}
        presets = yield self.electrode_server.get_presets()
        presets = json.loads(presets)

        for p in presets:
            self.electrode_parameters['presets'].update({str(p['id']): p['values']})

    @inlineCallbacks
    def get_e_channels(self):
        self.electrode_parameters['channels'] = {}
        e_channels = yield self.electrode_server.get_channels()
        e_channels = json.loads(e_channels)

        all_channels = yield self.sequencer_server.get_channels()
        all_channels = json.loads(all_channels)

        lookup = {}
        for k in all_channels.keys():
            lookup[k.split('@')[-1]] = k

        for k,v in e_channels.items():
            self.electrode_parameters['channels'][k] = lookup[v]

    @inlineCallbacks
    def refresh_sequencer_parameters(self, c=None, signal=None):
        conductor_parameters = yield self.conductor_server.get_parameter_values()
        self.sequencer_parameters = json.loads(conductor_parameters)['sequencer']

    @setting(1, "Refresh", returns='i')
    def refresh(self, c):
        try:
            yield self._refresh()
            returnValue(0)
        except Exception as e:
            print "Exception in SequenceVault.refresh: " + e
            returnValue(-1)

    @setting(2, "Get Sequences", returns='s')
    def get_sequences(self, c):
        sorted_list = sorted(self.sequences.keys(), key=lambda x: x[0].capitalize())
        return json.dumps(sorted_list)

    @setting(3, "Get Dates", sequence_name='s', returns='*s')
    def get_dates(self, c, sequence_name):
        try:
            return sorted(self.sequences[sequence_name].keys())
        except Exception as e:
            print "Exception in SequenceVault.get_dates: " + e 
            return []

    @setting(4, "Get Versions", sequence_name='s', returns='*s')
    def get_versions(self, c, sequence_name):
        try:
            s = []
            for date in sorted(self.sequences[sequence_name].keys()):
                for x in self.sequences[sequence_name][date]:
                    s.append(date + self.version_suffix + sequence_name + x)
            return s
        except Exception as e:
            print "Exception in SequenceVault.get_versions: " + e
            return ['']

    @setting(6, "Get Parameters", returns='s')
    def get_parameters(self, c):
        return json.dumps({'sequencer': self.sequencer_parameters,
                            'electrode': self.electrode_parameters})

    @setting(7, "Get Sequence Parameters", returns='s')
    def get_sequence_parameters(self, c):
        return json.dumps(self.sequencer_parameters)

    @setting(8, "Get Electrode Parameters", returns='s')
    def get_electrode_parameters(self, c):
        return json.dumps(self.electrode_parameters)

    @setting(5, "Get Parameterized Sequence", sequences='*s', returns='s')
    def get_parameterized_sequence(self, c, sequences):
        yield self._refresh()
        joined = self.join_sequences(sequences)
        (sequence, electrode_seq) = (joined['sequence'], joined['meta']['electrodes'])
        sequence = self.update_electrodes(
                 sequence,
                 electrode_seq,
                 self.electrode_parameters['presets'],
                 self.electrode_parameters['channels'])
        sequence = self.substitute_sequencer_parameters(sequence)
        returnValue(json.dumps(sequence))

    def join_sequences(self, sequences):
        seqs = []

        for s in sequences:
            # Get most recent version for now
            date = sorted(self.sequences[s].keys())[-1]
            path = self.sequence_path.format(date) + s
            
            with open(path, 'r') as f:
                seqs.append(json.load(f))

        out = seqs[0]
        for x in seqs[1:]:
            for key in out.keys():
                for k in out[key].keys():
                    out[key][k] += x[key][k]
        return out

    def update_electrodes(self, seq, e_seq, presets, channels):
        for name,loc in channels.items():
            # Get the sequence for the channel in question
            s = seq[loc]

            # Make sure these sequences are the same length!
            # If not, we will do nothing to this channel
            if len(e_seq) == len(s):
                # This will hold the fixed sequence for this channel
                fixed = []

                # Step through sequence
                for e_step in e_seq:
                    # Copy e_step to avoid aliasing
                    step = deepcopy(e_step)
                    # Keys 'vi' and 'vf' are ramp start and end voltages
                    for k in ['vi', 'vf']:
                        if step.has_key(k):
                            # Presets are labeled with integers in the sequence
                            # but the keys are strings in our dict, so cast to a str
                            p = str(step[k])

                            # If the preset exists, replace the p
                            if presets.has_key(p):
                                step[k] = presets[p][name]
                            else:
                                step[k] = presets['0'][name]
                                print "SequenceVault: electrode preset {} not found, replacing with 0".format(p)
                    fixed.append(step)
                seq.update({loc: fixed})
        return seq

    def substitute_sequencer_parameters(self, x):
        if type(x).__name__ in ['str', 'unicode']:
            if x[0] == '*': 
                return self.sequencer_parameters[x]
            else:
                return x
        elif type(x).__name__ == 'list':
            return [self.substitute_sequencer_parameters(xx) for xx in x] 
        elif type(x).__name__ == 'dict':
            return {k: self.substitute_sequencer_parameters(v) for k,v, in x.items()}
        else:
            return x

    def split_filename(self, filename):
        split = filename.split(self.version_suffix)

        if len(split) == 1:
            return (filename, '')
        else:
            fname = ''.join(split[:-1])
            suffix = split[-1]
            try:
                x = int(suffix[1:])
                return (fname, suffix)
            except:
                return (filename, '')

    def stopServer(self):
        pass

if __name__ == "__main__":
    from labrad import util
    util.runServer(SequenceVault())
