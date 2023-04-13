import json
import os

from datetime import date, timedelta
from itertools import chain
from time import strftime
from copy import deepcopy

from twisted.internet.defer import inlineCallbacks, returnValue

SEQUENCE_DIRECTORY = '/home/bialkali/data/{}/sequences/'
TIMING_CHANNEL = 'Trigger@D15'
YEARS = 2

def zero_sequence(dt):
    return {'dt': dt, 'type': 's', 'vf': 0}

@inlineCallbacks
def value_to_sequence(sequence, cxn):
    if type(sequence.value).__name__ == 'list':
        
        seqs = []
        e_seqs = []

        for x in sequence.value:
            out = read_sequence_file(sequence.sequence_directory, x)
            fixed_json = yield cxn.sequencer.fix_sequence_keys(json.dumps(out[0]))
            seq_fixed = json.loads(fixed_json)
            seqs.append(seq_fixed)
            e_seqs += out[1]

        returnValue((combine_sequences(seqs), e_seqs))
        
    else:
        returnValue("Error: Sequence parameter expects list as input")


# Presets is the value returned from electrode.get_presets()
def fix_electrode_presets(presets):
    ret = {}
    for p in presets:
        ret.update({str(p['id']): p['values']})
    return ret


# e_channels is a dict, {"LP": "S00", etc.}
# channels is the value returned from sequencer.get_channels(),
# which looks like {"SDAC0: Lower Plate (DAC: -V)@S00": {}, etc.}
def get_electrode_nameloc(e_channels, channels):
    ret = {}
    lookup = {}

    for key in channels.keys():
        lookup[key.split('@')[-1]] = key

    for key, val in e_channels.items():
        ret[key] = lookup[val]

    return ret

def update_electrode_values(seq, e_seq, presets, channels):
    # For each electrode channel
    for name, loc in channels.items():

        # Get the channel sequence
        s = seq[loc]

        # If no, don't touch the sequence, we'll just run whatever is in the file
        # If yes, then let's replace the values in the sequence:
        if len(e_seq) == len(s):

            fixed = []

            # For each step in the sequence
            for step, e_step in zip(s, e_seq):
                # Set step = e_step
                step = deepcopy(e_step)
                
                for k in ['vf', 'vi']:
                    if step.has_key(k):
                        v = str(step[k])

                        # Get the actual voltage from presets
                        if presets.has_key(v):
                            step[k] = presets[v][name]
                        else:
                            step[k] = presets['0'][name]
                            print("Preset {} not found, replaced with 0".format(int(v)))
                fixed.append(step)
            seq.update({loc: fixed})
    return seq

def read_sequence_file(sequence_directory, filename):
    # Sequencer control sends the actual sequence dict
    if type(filename).__name__ == 'dict':
        if filename.has_key('sequence'):
            try:
                return (filename['sequence'], filename['meta']['electrodes'])
            except:
                return (filename, [])
        else:
            return (filename, [])
    if not os.path.exists(filename):
        for i in range(365 * YEARS):
            day = date.today() - timedelta(i)
            path = sequence_directory.format(day.strftime('%Y%m%d')) + filename
            if os.path.exists(path):
                filename = path
                break
    with open(filename, 'r') as infile:
         sequence = json.load(infile)

    s = {}
    try:
        s = sequence['sequence']
    except KeyError:
        s = sequence

    # Get electrode sequence
    timing = s[TIMING_CHANNEL]
    try:
        electrode_seq = sequence['meta']['electrodes']
    except KeyError:
        electrode_seq = []

    if len(electrode_seq) != len(timing):
        electrode_seq = [zero_sequence(v['dt']) for v in timing]

    return (s, electrode_seq)


def combine_sequences(sequence_list):
    combined_sequence = sequence_list.pop(0)
    for sequence in sequence_list:
        for k in sequence.keys():
            combined_sequence[k] += sequence[k]
    return combined_sequence

def get_parameters(x):
    """ determine which parameters we need to get from conductor or db """
    if type(x).__name__ in ['str', 'unicode'] and x[0] == '*':
        return [x]
    elif type(x).__name__ == 'list':
        return list(chain.from_iterable([get_parameters(xx) for xx in x]))
    elif type(x).__name__ == 'dict':
        return list(chain.from_iterable([get_parameters(v) for v in x.values()]))
    else:
        return []

def substitute_sequence_parameters(x, parameter_values):
    if type(x).__name__ in ['str', 'unicode']:
        if x[0] == '*':
            return parameter_values[x]
        else:
            return x
    elif type(x).__name__ == 'list':
        return [substitute_sequence_parameters(xx, parameter_values) for xx in x]
    elif type(x).__name__ == 'dict':
        out = {}
        for k, v in x.items:
            out[k] = substitute_sequence_parameters(v, parameter_values)
            if k == "dt" and out[k] <= 0:
                raise ValueError("Time {} is {} but must be positive! Sad!".format(k, out[k]))
        return out
    else:
        return x

def get_duration(sequence):
    return max([sum([s['dt'] for s in cs]) for cs in sequence.values()])

