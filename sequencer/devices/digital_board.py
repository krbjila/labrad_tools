import json
from twisted.internet.defer import inlineCallbacks, returnValue

from server_tools.device_server import DeviceWrapper

T_TRIG = 10e-6
# T_TRIG = 0
T_END = 1e0
TRIGGER_CHANNEL = 'Trigger@D15'

def time_to_ticks(clk, time):
    return int(clk*time)

def get_out(channel_sequence, t):
    for s in channel_sequence[::-1]:
        if s['t'] <= t:
            # 7/2/2021: changed below to support possibly negative values
            # for sequence outputs. We consider anything positive to be 'on'
            return 1 if s['out'] > 0 else 0

class DigitalChannel(object):
    def __init__(self, config):
        """ defaults """
        self.channel_type = 'digital'
        self.mode = 'auto'
        self.manual_output = 0
        self.invert = 0

        row, col = config['loc']
        self.rowcol = [row, col]
        self.name = 'TTL'+row+str(col).zfill(2)
        
        """ non-defaults """
        for key, value in config.items():
            setattr(self, key, value)
         
        self.loc = row+str(col).zfill(2)
        self.key = self.name+'@'+self.loc
   
    @inlineCallbacks
    def set_mode(self, mode):
        self.mode = mode
        yield self.board.write_channel_modes()

    @inlineCallbacks
    def set_manual_output(self, state):
        self.manual_output = state
        yield self.board.write_channel_manual_outputs()

class DigitalBoard(DeviceWrapper):
    sequencer_type = 'digital'
    def __init__(self, config):
        """ defaults """
        self.update_parameters = []
        self.init_commands = []

        # removed KM 08/10/2017
        # self.bitfile = 'digital_sequencer.bit'
        self.mode_ints = {'idle': 0, 'load': 1, 'run': 2}
        self.mode_wire = 0x00
        self.sequence_pipe = 0x80
        self.channel_mode_wires = [0x01, 0x03, 0x05, 0x07]
        self.state_invert_wires = [0x02, 0x04, 0x06, 0x08]
        self.clk = 50e6
        self.mode = 'idle'
       
        channel_wrappers = [
                DigitalChannel({'loc': [x, i], 'board_name': self.name})
                for x in self.name for i in range(16)]

        """ non-defaults"""
        for key, value in config.items():
            setattr(self, key, value)

        # added KM 08/10/2017    
        if self.address == 'KRbDigi01':    
            self.bitfile = 'digital_lower_drive_no_zero.bit'
        else:
            self.bitfile = 'digital_triggered.bit'

        for c in self.channels:
            c['board_name'] = self.name
            wrapper = DigitalChannel(c)
            row, column = wrapper.rowcol
            if row < 'E':
                channel_wrappers[(ord(row)%32-1)*16 + column] = wrapper
            else:
            #If the row does not start at 'A', indexing is wrong. Change so index starts at 'A' (thus the -4)
                channel_wrappers[((ord(row)-4)%32-1)*16 + column] = wrapper
        self.channels = channel_wrappers

        for c in self.channels:
            c.board = self
        
        super(DigitalBoard, self).__init__({})

    @inlineCallbacks
    def initialize(self):
        yield self.connection.program_bitfile(self.bitfile)
        yield self.write_channel_modes()
        yield self.write_channel_manual_outputs()

    @inlineCallbacks
    def set_mode(self, mode):
        mode_int = self.mode_ints[mode]
        yield self.connection.set_wire_in(self.mode_wire, mode_int)
        yield self.connection.update_wire_ins()
        self.mode = mode

    @inlineCallbacks
    def program_sequence(self, sequence):
        byte_array = self.make_sequence_bytes(sequence)
        yield self.set_mode('idle')
        yield self.set_mode('load')
        yield self.connection.write_to_pipe_in(self.sequence_pipe, json.dumps(byte_array))
        yield self.set_mode('idle')

    @inlineCallbacks
    def start_sequence(self):
        yield self.set_mode('run')

    def make_sequence_bytes(self, sequence):
        # make sure trigger happens on first run
        if self.address == 'KRbDigi01':        
            for c in self.channels:
                s = {'dt': T_TRIG, 'out': sequence[c.key][0]['out']}
                sequence[c.key].insert(0, s)

        # trigger other boards
        # Note: Trigger channel is inverted!
        for s in sequence[TRIGGER_CHANNEL]:
            s['out'] = False
        sequence[TRIGGER_CHANNEL][0]['out'] = True
        # allow for analog's ramp to zero, last item will not be written
        sequence[TRIGGER_CHANNEL].append({'dt': T_END, 'out': True})

        for c in self.channels:
            total_ticks = 0
            for s in sequence[c.key]:
                dt = time_to_ticks(self.clk, s['dt'])
                s.update({'dt': dt, 't': total_ticks})
                total_ticks += dt

        # each sequence point updates all outs for some number of clock ticks
        # since some channels may have different 'dt's, every time any channel 
        # changes state we need to write all channel outs.
        t_ = sorted(list(set([s['t'] for c in self.channels 
                                     for s in sequence[c.key]])))
        dt_ = [t_[i+1] - t_[i] for i in range(len(t_)-1)] + [time_to_ticks(self.clk, T_END)]

        programmable_sequence = [(dt, [get_out(sequence[c.key], t) 
                for c in self.channels])
                for dt, t in zip(dt_, t_)]
        
        byte_array = []
        for t, l in programmable_sequence:
            # each point in sequence specifies all 64 logic outs with 64 bit number
            # e.g. all off is 0...0, channel 1 on is 10....
            byte_array += list([sum([2**j for j, b in enumerate(l[i:i+8]) if b]) 
                    for i in range(0, 64, 8)])
            # time to keep these outs is 32 bit number in units of clk ticks
            byte_array += list([int(eval(hex(t)) >> i & 0xff) 
                    for i in range(0, 32, 8)])
        byte_array += [0]*24
        return byte_array
    
    @inlineCallbacks
    def write_channel_modes(self):
        cm_list = [c.mode for c in self.channels]
        values = [sum([2**j for j, m in enumerate(cm_list[i:i+16]) 
                if m == 'manual']) for i in range(0, 64, 16)]
        for value, wire in zip(values, self.channel_mode_wires):
            yield self.connection.set_wire_in(wire, value)
        yield self.connection.update_wire_ins()
        yield self.write_channel_manual_outputs()
   
    @inlineCallbacks
    def write_channel_manual_outputs(self): 
        cm_list = [c.mode for c in self.channels]
        cs_list = [c.manual_output for c in self.channels]
        ci_list = [c.invert for c in self.channels]
        values = [sum([2**j for j, (m, s, i) in enumerate(zip(
                cm_list[i:i+16], cs_list[i:i+16], ci_list[i:i+16]))
                if (m=='manual' and s!=i) or (m=='auto' and i==True)]) 
                for i in range(0, 64, 16)]
        for value, wire in zip(values, self.state_invert_wires):
            yield self.connection.set_wire_in(wire, value)
        yield self.connection.update_wire_ins()
