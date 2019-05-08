import numpy as np
import json
import math

from twisted.internet.defer import inlineCallbacks, returnValue

from server_tools.device_server import DeviceWrapper
from lib.ad5791_ramps import RampMaker

(VREFN, VREFP) = (-10., 10.)
(VMIN, VMAX) = (-5, 5)
DAC_BITS = 20
DT_BITS = 28

FPGA_CLOCK = 4e6
N_CHANNELS = 6

RAM_DEPTH = 8
MAX_STEPS = (2**RAM_DEPTH - 1) / 3 - 1

TICKS_TO_OUTPUT = 31 # Number of clock cycles to output 1 value
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
        
        self.loc = self.board_name + str(self.loc).zfill(2)
        self.key = self.name+'@'+self.loc


class AD5791Board(DeviceWrapper):
    sequencer_type = 'ad5791'
    def __init__(self, config):
        """ defaults """
        self.update_parameters = []
        self.init_commands = []

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

        super(AD5791Board, self).__init__({})

    @inlineCallbacks
    def initialize(self):
        yield self.connection.program_bitfile(self.bitfile)
        yield self.set_mode('idle')
        yield self.set_mode('reset')
        yield self.set_mode('init')
        yield self.set_mode('idle')

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
            index = int(c.loc[1:-1])
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


    def make_sequence_bytes(self, sequence):
        """ 
        take readable {channel: [{}]} to programmable [end_voltage[20], duration[28]]
        """

        byte_array = {}
        for c in self.channels:
            index = c.loc
            byte_array[index] = []

            # Generate the list of ramps from the sequence
            ramps = RampMaker(sequence[c.key]).get_programmable()

            # Consolidate ramps:
            # The amount of RAM is limited on the FPGA
            # Each linear ramp counts as a step
            # Want to consolidate these to avoid taking up too much memory
            #
            # Keep track of the last value
            # and any accumulated time
            last_v = ramps[0]['v']
            dt_accumulated = 0 
            consolidated_ramps = []

            for i in range(len(ramps)):
                r = ramps[i]
                
                # Be careful with the first ramp in the sequence
                # Since we don't actually know what the last_v should be 
                if i == 0:
                    if r['dt'] < MIN_TIME:
                        consolidated_ramps.append({'dt': MIN_TIME, 'v': r['v']})
                        dt_accumulated = r['dt'] - MIN_TIME
                    else:
                        consolidated_ramps.append({'dt': r['dt'], 'v': r['v']})
                        dt_accumulated = 0
                    last_v = r['v']
                # If at the end of the list, don't forget to add the last ramp
                elif i == len(ramps) - 1:
                    dt_accumulated += r['dt']
                    consolidated_ramps.append({'dt': max(dt_accumulated, MIN_TIME), 'v': r['v']})
                else:
                    # If this step has the same voltage as the last,
                    # consolidate into a single step
                    if r['v'] == last_v:
                        dt_accumulated += r['dt']
                    # Otherwise, the voltage is changing
                    else:
                        # MIN_TIME is the time to output a single voltage
                        # In this case, we have time to do this
                        if dt_accumulated > MIN_TIME:
                            consolidated_ramps.append({'dt': dt_accumulated, 'v': last_v})
                            dt_accumulated = 0
                        # In this case, the requested step is shorter than what we can do
                        # Do our best by setting a step with MIN_TIME
                        # Subtract MIN_TIME from dt_accumulated to keep track of the accumulated timing error
                        # This error will end up being subtracted from the next long step
                        else:
                            consolidated_ramps.append({'dt': MIN_TIME, 'v': last_v})
                            dt_accumulated -= MIN_TIME
                        last_v = r['v']
                        dt_accumulated += r['dt']    

            
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
                print "Too many steps! Program will be truncated!!!"
         
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
                for i in range(0, 4):
                    dtbits.append(int((r['dt'] >> 8*i) & 0xff))

                dvbits = []
                for i in range(0, 3):
                    dvbits.append(int((r['v'] >> 8*i) & 0xff))

                bits = dvbits[0:2] + [dvbits[2] + dtbits[0]] + dtbits[1:4]

                byte_array[index] += bits

            # Pad
            byte_array[index] += [0]*6

        return byte_array
