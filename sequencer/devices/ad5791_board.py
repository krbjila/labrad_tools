import numpy as np
import json
import math
import sys

import labrad
from twisted.internet.defer import inlineCallbacks, returnValue

sys.path.append('../..')
from server_tools.device_server import DeviceWrapper
from lib.ad5791_ramps import RampMaker

(VREFN, VREFP) = (-5., 5.)
(VMIN, VMAX) = (-2.6, 2.6)
DAC_BITS = 20
DT_BITS = 28

FPGA_CLOCK = 4e6
N_CHANNELS = 6

RAM_DEPTH = 10
MAX_STEPS = (2**RAM_DEPTH - 1) / 3 - 1

MIN_TICKS_TO_OUTPUT = 31 # Number of clock cycles to output 1 value
# Let's pad this a bit to be safe
TICKS_TO_OUTPUT = 40
MIN_TIME = float(TICKS_TO_OUTPUT) / FPGA_CLOCK
MAX_TIME = (2**DT_BITS - 1) / float(FPGA_CLOCK)

def time_to_ticks(clk, time):
    if time > MAX_TIME:
        return -1
    return max(int(abs(clk*time)), 1)

# 2's complement
def calcD(v):
    CONV_FACTOR = 2**DAC_BITS - 1

    if v > VMAX:
        v = VMAX 
    elif v < VMIN:
        v = VMIN

    if v >= VREFP:
        v = VREFP - (VREFP - VREFN) / CONV_FACTOR
    elif v < VREFN:
        v = VREFN

    if v >= 0:
        return long(CONV_FACTOR * v / (VREFP - VREFN))
    else:
        return long(CONV_FACTOR * (VREFP - VREFN + v) / (VREFP - VREFN) + 1)


class AD5791Channel(object):
    """ wrapper for single analog channel on yesr dacbord 

    example_config = {
        'loc': 0, # in range(8)
        'name': 'DACA0', # unique string 
        'mode': 'auto', # 'auto' or 'manual'
        'manual_output': 0, # default manual voltage. between -10, 10.
    }
    """
    def __init__(self, config):
        """ defaults """
        self.channel_type = 'ad5791'
        self.mode = 'auto'
        board_name = config['board_name']
        loc = config['loc']
        self.name = 'DAC'+board_name+str(loc).zfill(2)
        self.voltage_range = [-10., 10.]
        
        """ non-defaults """
        for key, value in config.items():
            setattr(self, key, value)
        
        self.index = self.loc 
        self.loc = self.board_name + str(self.loc).zfill(2)
        self.key = self.name+'@'+self.loc


class AD5791Board(DeviceWrapper):
    sequencer_type = 'ad5791'
    def __init__(self, config):
        """ defaults """
        self.update_parameters = []
        self.init_commands = []

        self.name = "Boardy McBoardface"
        self.bitfile = 'ad5791.bit'
        self.mode_ints = {'idle': 0, 'reset': 1, 'init': 2, 'load': 3, 'run': 4}
        self.mode_wire = 0x00
        self.channel_wire = 0x01
        self.reset_trigger = 0x40
        self.sequence_pipe = 0x80
        
        self.clk =  FPGA_CLOCK
        self.mode = 'idle'
        self.load_channel = 0

        channel_wrappers = [AD5791Channel({'loc': i, 'board_name': self.name})
                            for i in range(N_CHANNELS)]

        """ non-defaults"""
        for key, value in config.items():
            setattr(self, key, value)
        
        for c in self.channels:
            c['board_name'] = self.name
            wrapper = AD5791Channel(c)
            channel_wrappers[c['loc']] = wrapper

        self.channels = channel_wrappers

        for c in self.channels:
            c.board = self

        self.connect()

        super(AD5791Board, self).__init__({})

    @inlineCallbacks
    def initialize(self):
        yield self.connection.program_bitfile(self.bitfile)
        yield self.set_mode('idle')
        yield self.set_mode('reset')
        yield self.set_mode('idle')
        yield self.set_mode('init')
        yield self.set_mode('idle')

    def connect(self):
        self.cxn = labrad.connect()
        try:
            servers = self.cxn.servers
            electrode = [s for s in servers if "electrode" in s][0]
            self.server = self.cxn[electrode]
        except Exception as e:
            print("Could not connect to electrode server. Smooth ramps will be replaced by linear ramps: {}".format(e))

    @inlineCallbacks
    def set_mode(self, mode):
        mode_int = self.mode_ints[mode]
        yield self.connection.set_wire_in(self.mode_wire, mode_int)
        yield self.connection.update_wire_ins()
        self.mode = mode

    @inlineCallbacks
    def set_load_channel(self, channel):
        yield self.connection.set_wire_in(self.channel_wire, channel)
        yield self.connection.update_wire_ins()
        self.load_channel = channel

    @inlineCallbacks
    def program_sequence(self, sequence):
        byte_array = self.make_sequence_bytes(sequence)
        yield self.set_mode('idle')
        yield self.set_mode('load')

        for c in self.channels:
            index = c.index
            yield self.set_load_channel(index)
            yield self.connection.write_to_pipe_in(self.sequence_pipe, json.dumps(byte_array[c.loc]))
        yield self.set_mode('idle')

    @inlineCallbacks
    def start_sequence(self):
        yield self.set_mode('idle')
        yield self.set_mode('run')

    @inlineCallbacks
    def issue_master_reset(self):
        yield self.connection.activate_trigger_in(self.reset_trigger, 0)

    @staticmethod
    def get_short_name(name):
        """
        get_short_name(name)

        Gets the short name of an electrode, to be used in queries to the electrode server

        Args:
            name (str): The electrode channel's name

        Returns:
            str: The short name of the electrode
        """
        if "Upper West" in name:
            return "UW"
        elif "Upper East" in name:
            return "UE"
        elif "Lower East" in name:
            return "LE"
        elif "Lower West" in name:
            return "LW"
        elif "Upper Plate" in name:
            return "UP"
        elif "Lower Plate" in name:
            return "LP"
        else:
            raise(ValueError("Electrode name {} not recognized".format(name)))


    def make_sequence_bytes(self, sequence):
        """ 
        take readable {channel: [{}]} to programmable [end_voltage[20], duration[28]]
        """

        # Create a dictionary (indexed by channel) of lists (indexed by column) to record the ramps once the smooth ramps are expanded
        expanded_ramps = {}
        for c in self.channels:
            expanded_ramps[c.key] = []

        # Query the electrode server to find parameters for smooth ramps
        electrodes = ["LP", "UP", "LW", "UW", "LE", "UE"]
        vi = {}
        for e in electrodes:
            vi[e] = 0.0

        n_ramps = len(sequence[self.channels[0].key])
        for i in range(n_ramps):
            if sequence[self.channels[0].key][i]["type"] == "smooth":
                try:
                    # Determine final voltages for each channel
                    vf = {}
                    for c in self.channels:
                        vf[AD5791Board.get_short_name(c.key)] = sequence[c.key][i]["vf"]
                    params_query = json.dumps({"vi": [vi], "vf": [vf]})
                    # Query parameters (bias, angle, dEdy, dEdx, ...) of initial and final fields
                    params = json.loads(self.server.get_params(params_query))
                    # Determine step size and dt per ramp
                    if "n" in sequence[self.channels[0].key][i]:
                        n_steps = sequence[self.channels[0].key][i]["n"]
                    else:
                        n_steps = 10
                    dt = sequence[self.channels[0].key][i]["dt"] / n_steps
                    # Determine series of intermediate voltages for the smooth ramp
                    v_query = {"ramp": []}
                    for s in range(n_steps):
                        step_params = {}
                        for k in params["vi"][0].keys():
                            p_i = params["vi"][0][k]
                            p_f = params["vf"][0][k]
                            step_params[k] = p_i + (p_f - p_i) * (float(s) / n_steps)
                        # If on the first step, define the initial guess
                        if s == 0:
                            step_params.update(vi)
                        v_query["ramp"].append(step_params)
                    # Query electrode voltages for ramps
                    ramps = json.loads(self.server.get_ramps(json.dumps(v_query)))
                    # Add linear ramps to sequence
                    for c in self.channels:
                        for r in ramps["ramp"][1:]:
                            vf_ramp = r[AD5791Board.get_short_name(c.key)]
                            c_ramp = {"type": "lin", "dt": dt, "vf":vf_ramp}
                            expanded_ramps[c.key].append(c_ramp)
                        # Add a final ramp to the last voltage
                        vf_ramp = vf[AD5791Board.get_short_name(c.key)]
                        c_ramp = {"type": "lin", "dt": dt, "vf":vf_ramp}
                        expanded_ramps[c.key].append(c_ramp)
                except Exception as e:
                    print("Could not add smooth ramp, using linear ramp: {}".format(e))
                    ramp = sequence[c.key][i]
                    ramp["type"] = "lin"
                    expanded_ramps[c.key].append(ramp)
            else:
                # If not a smooth ramp, add to the sequence
                for c in self.channels:
                    expanded_ramps[c.key].append(sequence[c.key][i])
            # Update initial voltages for next ramp
            for c in self.channels:
                vi[AD5791Board.get_short_name(c.key)] = sequence[c.key][i]["vf"]
                
        byte_array = {}
        for c in self.channels:
            byte_array[c.loc] = []

            # Generate the list of ramps from the sequence
            ramps = RampMaker(expanded_ramps[c.key]).get_programmable()

            # Consolidate ramps:
            # The amount of RAM is limited on the FPGA
            # Each linear ramp counts as a step
            # Want to consolidate these to avoid taking up too much memory
            consolidated_ramps = []

            # First walk through the ramp array and remove any redundancy
            # Redundant ramps are when we have 3 ramps with the same setpoint in a row
            # In this case we can consolidate the second 2
            c_ramps = ramps[0:2]
            for i in range(2, len(ramps)):
                r = ramps[i]
                rm = ramps[i-1]
                rmm = ramps[i-2]

                if r['v'] == rm['v'] and r['v'] == rmm['v']:
                    rp = c_ramps.pop()
                    c_ramps.append({'dt': r['dt']+rp['dt'], 'v': r['v']})
                else:
                    c_ramps.append(r)

            # Now enforce the MIN_TIME to update the DAC
            # dt_accumulated is the accumulated error due to ramps being requested too fast
            #
            # When this happens, we will just output as fast as we can until there is a
            # long enough block where we can catch up to the sequence
            dt_accumulated = 0
            for r in c_ramps:
                dt_accumulated += r['dt']
                if dt_accumulated < MIN_TIME:
                    consolidated_ramps.append({'dt': MIN_TIME, 'v': r['v']})
                    dt_accumulated -= MIN_TIME
                else:
                    consolidated_ramps.append({'dt': dt_accumulated, 'v': r['v']})
                    dt_accumulated = 0


            # Need to check that we haven't created any ramps that are
            # longer than the maximum ramp time.
            # If we did, then just need to split the ramp.
            final_ramps = []
            for r in consolidated_ramps:
                if r['dt'] > MAX_TIME:
                    n_steps = math.ceil(r['dt'] / MAX_TIME)
                    dt = float(r['dt']) / n_steps
                    for i in range(n_steps):
                        v = last_v + (r['v'] - last_v) * float(i+1) / n_steps
                        final_ramps.append({'dt': dt, 'v': v})
                else:
                    final_ramps.append(r)

            # Print a warning if there are too many ramps
            if len(final_ramps) > MAX_STEPS:
                print("Too many steps! Program will be truncated!!!")
         
            # Trucate the array at the maximum program length 
            try:
                final_ramps = final_ramps[0:MAX_STEPS]
            except: pass

            # Convert final ramps to sequence bytes
            for r in final_ramps:
                r['dt'] = time_to_ticks(self.clk, r['dt'])
                r['dt'] = r['dt'] << 4

                r['v'] = calcD(r['v'])

                dtbits = []
                for i in range(4):
                    dtbits.append(int((r['dt'] >> 8*i) & 0xff))

                dvbits = []
                for i in range(3):
                    dvbits.append(int((r['v'] >> 8*i) & 0xff))

                bits = dvbits[0:2] + [dvbits[2] + dtbits[0]] + dtbits[1:]

                byte_array[c.loc] += bits

            # Pad
            byte_array[c.loc] += [0]*6

        return byte_array

if __name__ == "__main__":
    config_file = "/Users/cal/labrad_tools/sequencer/config.json"
    with open(config_file, "r") as f:
        config = json.load(f)

    filename = "/Users/cal/Downloads/sequence_06-06-21_15-08-16.json"
    # filename = "/Users/cal/Downloads/sequence_06-06-21_15-08-29.json"
    with open(filename, "r") as f:
        sequence = json.load(f)

    board_config = config["devices"]["S"]
    board_config["name"] = "S"
    board = AD5791Board(board_config)
    sequence_bytes = board.make_sequence_bytes(sequence)
    print(sequence_bytes)