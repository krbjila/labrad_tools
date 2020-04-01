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
        """ Setup Labrad connections, _refresh"""

        # Connect to needed servers as a client
        self.electrode_server = self.client.servers[self.electrode_servername]
        self.sequencer_server = self.client.servers[self.sequencer_servername]
        self.conductor_server = self.client.servers[self.conductor_servername]

        # Connect to electrode's presets_changed signal
        # This is needed to keep sequence updated when
        # electrode presets are changed in the electrode_control gui
        self.electrode_server.signal__presets_changed(self.electrode_presets_changed_id)
        self.electrode_server.addListener(listener=self.refresh_electrode_parameters,
                                            source=None, ID=self.electrode_presets_changed_id)

        # Connect to conductor's parameters_updated signal
        # This is needed to keep sequence updated when
        # conductor parameters (e.g., sequence variables '*xxx') are updated
        self.conductor_server.signal__parameters_updated(self.conductor_parameters_updated_id)
        self.conductor_server.addListener(listener=self.refresh_sequencer_parameters,
                                            source=None, ID=self.conductor_parameters_updated_id)
        # Update everything
        yield self._refresh()

    @inlineCallbacks
    def _refresh(self):
        """
        Update everything:
            List of sequences and versions
            Electrode Parameters
            Sequencer parameters
        """
        self.refresh_sequences()
        yield self.refresh_electrode_parameters()
        yield self.refresh_sequencer_parameters()

    def refresh_sequences(self):
        """
        Update sequence and version dictionary
        """

        # Empty self.sequences
        # Will have format: {sequence_name: {date: [versions]}}
        self.sequences = {}

        # Check up to 1 year back
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
        """
        Get electrode presets from electrode server
        """
        self.electrode_parameters['presets'] = {}
        presets = yield self.electrode_server.get_presets()
        presets = json.loads(presets)

        for p in presets:
            # Presets is a list of dicts {'id': id, 'values': {values}}
            # For convenience, turn it into a dict, with key str(id)
            self.electrode_parameters['presets'].update({str(p['id']): p['values']})

    @inlineCallbacks
    def get_e_channels(self):
        """
        Get the nameloc (sequence file key) for the electrode channels

        Electrode presets are stored as dicts with keys that are the
        short names of the electrodes (e.g., LP, LW. UE, etc.)

        Electrode channels are stored (by the electrode server) in the form
        {short: loc} (e.g., {'LP': 'S00'})

        Sequence files are dicts with keys that are the nameloc
        (e.g., "Lower Plate (-V)@S00" etc.)

        self.electrode_parameters['channels'] is a dict that looks like {short: nameloc}
        (e.g., {'LP': 'Lower Plate (-V)@S00'})
        """
        # Dump channels dict
        self.electrode_parameters['channels'] = {}
        
        # Get electrode and sequencer channels
        e_channels = yield self.electrode_server.get_channels()
        e_channels = json.loads(e_channels)
        all_channels = yield self.sequencer_server.get_channels()
        all_channels = json.loads(all_channels)

        # Make a dict to lookup namelocs by loc
        lookup = {}
        for k in all_channels.keys():
            lookup[k.split('@')[-1]] = k

        for k,v in e_channels.items():
            self.electrode_parameters['channels'][k] = lookup[v]

    @inlineCallbacks
    def refresh_sequencer_parameters(self, c=None, signal=None):
        """
        Get the sequencer parameters from conductor
        """
        conductor_parameters = yield self.conductor_server.get_parameter_values()
        self.sequencer_parameters = json.loads(conductor_parameters)['sequencer']

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

    @setting(2, "Get Sequences", returns='*s')
    def get_sequences(self, c):
        """
        Get list of available sequences

        Returns:
            List of sequences
        """
        sorted_list = sorted(self.sequences.keys(), key=lambda x: x[0].capitalize())
        return sorted_list

    @setting(3, "Get Dates", sequence_name='s', returns='*s')
    def get_dates(self, c, sequence_name):
        """
        Get available dates for a sequence

        Inputs:
            sequence_name: str

        Returns:
            List of dates
        """
        try:
            return sorted(self.sequences[sequence_name].keys())
        except Exception as e:
            print "Exception in SequenceVault.get_dates: " + e 
            return []

    @setting(4, "Get Versions", sequence_name='s', returns='*s')
    def get_versions(self, c, sequence_name):
        """
        Get available versions of a sequence

        Inputs:
            sequence_name: str

        Returns:
            List of sequence versions
            format: date__sequencename__version
        """
        try:
            s = []
            for date in sorted(self.sequences[sequence_name].keys()):
                for x in self.sequences[sequence_name][date]:
                    s.append(date + self.version_suffix + sequence_name + x)
            return s
        except Exception as e:
            print "Exception in SequenceVault.get_versions: " + e
            return ['']

    @setting(5, "Get Parameters", returns='s')
    def get_parameters(self, c):
        """
        Get electrode and sequencer parameters

        Returns:
            json.dumps({'sequencer': sequencer_parameters,
                        'electrode': electrode_parameters})
        """
        yield self._refresh()
        returnValue(json.dumps({'sequencer': self.sequencer_parameters,
                            'electrode': self.electrode_parameters}))

    @setting(6, "Get Sequence Parameters", returns='s')
    def get_sequence_parameters(self, c):
        """
        Get sequencer parameters from conductor

        Returns:
            json.dumps(sequencer_parameters)
        """
        yield self._refresh()
        returnValue(json.dumps(self.sequencer_parameters))

    @setting(7, "Get Electrode Parameters", returns='s')
    def get_electrode_parameters(self, c):
        """
        Get electrode parameters from electrode server

        Returns:
            json.dumps(electrode_parameters)
        """
        yield self._refresh()
        returnValue(json.dumps(self.electrode_parameters))

    @setting(8, "Get Substituted Sequence", sequences='*s', date='s', parameter_values='s', returns='s')
    def get_substituted_sequence(self, c, sequences, date=None, parameter_values=None):
        """
        Get the sequence, with electrode and sequencer parameters substituted

        With the "date" parameter, get the most recent sequence versions as of "date"
        Without the "date" parameter, get the most recent sequence versions as of now

        Without the "parameter_values" parameter, use most current parameter values from conductor server
        If "parameter_values" are included, these override the most current parameter values
        
        Input:
            sequences: list of sequence names
            parameter_values (optional): json.dumps'ed dict of parameter values to substitute
            date (optional): date string in '%Y%m%d' format
    
        Returns:
            json.dumps(sequence)
        """
        # Make sure parameters are up to date
        yield self._refresh()
        # Join sequences
        joined = self.join_sequences(sequences, date)
        # Get electrode sequence
        (sequence, electrode_seq) = (joined['sequence'], joined['meta']['electrodes'])

        # Substitute electrode values in the sequence with the values
        # defined by electrode_seq and self.electrode_parameters['presets']
        sequence = self.update_electrodes(
                 sequence,
                 electrode_seq,
                 self.electrode_parameters['presets'],
                 self.electrode_parameters['channels'])
        
        # Try to override values in sequencer_parameters
        # with parameter_values
        try:
            # deepcopy to avoid changing self.sequencer_parameters
            pv = deepcopy(self.sequencer_parameters).update(json.loads(parameter_values))
        except:
            pv = self.sequencer_parameters

        # Substitute in sequencer variables (e.g., '*X')
        sequence = self.substitute_sequencer_parameters(sequence, pv)
        returnValue(json.dumps(sequence))

    @setting(9, "Get Joined Sequence", sequences='*s', date='s', returns='s')
    def get_joined_sequence(self, c, sequences, date=None):
        """
        Get the sequence, without substituting parameters
        With the "date" parameter, get the most recent sequence versions as of "date"
        Without the "date" parameter, get the most recent sequence versions as of now

        Input:
            sequences: list of sequence names
            date (optional): date string in %Y%m%d format 

        Returns:
            json.dumps(joined_sequence):
                joined_sequence looks like {'meta': {'descriptions': [], 'electrodes': []},
                                            'sequence': {}}
        """
        # Make sure parameters are up to date
        yield self._refresh()
        # Join sequences
        joined = self.join_sequences(sequences, date)
        returnValue(json.dumps(joined))

    def join_sequences(self, sequences, date=None):
        """
        Joins a list of sequences
        With the "date" parameter, gets the most recent sequence versions as of "date"
        Without the date parameter, gets the most recent sequence versions as of now

        Input: 
            sequences: list of sequence names
            date (optional): date string in %Y%m%d format

        Returns:
            json.dumps(joined_sequence):
        """
        seqs = []

        for s in sequences:
            if date == None:
                # Get most recent version for now
                d = sorted(self.sequences[s].keys())[-1]
                path = self.sequence_path.format(d) + s
            else:
                # List of dates from newest to oldest
                dates = reversed(sorted(self.sequences[s].keys()))
                # The target date
                target_date = datetime.datetime.strptime(date, self.time_format)
                
                # Step through sequence dates
                for d in dates:
                    # For the first date that is the same or older than target_date,
                    # get the sequence path
                    if d <= target_date:
                        path = self.sequence_path.format(d) + s
                        break

            # Load the sequence file
            with open(path, 'r') as f:
                seqs.append(json.load(f))

        # Join
        out = seqs[0]
        for x in seqs[1:]:
            for key in out.keys():
                for k in out[key].keys():
                    out[key][k] += x[key][k]
        return out


    def update_electrodes(self, seq, e_seq, presets, channels):
        """
        Replace electrode values in the seq with the correct values
        defined by presets, e_seq
        """
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

    def substitute_sequencer_parameters(self, x, parameter_values):
        """
        Substitute sequencer parameters (e.g., '*XXX') into sequence
        """
        if type(x).__name__ in ['str', 'unicode']:
            if x[0] == '*': 
                return parameter_values[x]
            else:
                return x
        elif type(x).__name__ == 'list':
            return [self.substitute_sequencer_parameters(xx, parameter_values) for xx in x] 
        elif type(x).__name__ == 'dict':
            return {k: self.substitute_sequencer_parameters(v, parameter_values) for k,v, in x.items()}
        else:
            return x

    def split_filename(self, filename):
        """
        Split the filenames to get the version name

        Not really useful yet -- will be updated when we implement versioning
        """
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
        try:
            yield self.conductor_server.removeListener(listener=self.refresh_sequencer_parameters,
                                                        ID=self.conductor_parameters_changed_ID)
            yield self.electrode_server.removeListener(listener=self.refresh_electrode_parameters,
                                                        ID=self.electrode_presets_changed_ID)
        except:
            pass

if __name__ == "__main__":
    from labrad import util
    util.runServer(SequenceVault())
