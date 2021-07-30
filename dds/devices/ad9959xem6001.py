import json
from twisted.internet.defer import inlineCallbacks, returnValue
import sys

from pathlib import Path
sys.path.append([str(i) for i in Path(__file__).parents if str(i).endswith("labrad_tools")][0])
from server_tools.device_server import DeviceWrapper

from time import sleep

### DDS parameters ####

MULTIPLIER = 20
VCOGAIN = 1 # 1 for on, 0 for off
CLOCK = 20

class ddsChannel(object):
    def __init__(self, config):
        """ defaults """
        self.channel_type = 'dds'

        self.loc = config['loc']
        self.name = config['name']

        self.frequency = 0

        self.key = self.name + '@{},{}'.format(self.loc[0], self.loc[1])

        """ non-defaults """
        for key, value in config.items():
            setattr(self, key, value)

class ad9959xem6001(DeviceWrapper):
    # DDS Parameters
    clk = CLOCK
    multiplier = MULTIPLIER
    vcogain = VCOGAIN
    bits = 32
    numchannels = 12

    def __init__(self, config):
        """ defaults """
        self.update_parameters = []
        self.init_commands = []

        self.bitfile = 'dds3_ad9959.bit'
        self.data_wires = [0x00, 0x01, 0x02]

        self.current_values = [None]*self.numchannels

        """ non-defaults"""
        for key, value in config.items():
            setattr(self, key, value)

        channel_wrappers = [None]*self.numchannels
        for c in self.channels:
            c['board_name'] = self.name
            wrapper = ddsChannel(c)
            board, channel = wrapper.loc
            channel_wrappers[4*board + channel] = wrapper
        self.channels = channel_wrappers

        for c in self.channels:
            c.board = self
      
        super(ad9959xem6001, self).__init__({})

    @inlineCallbacks
    def initialize(self):
        yield self.connection.program_bitfile(self.bitfile)

    def getValue(self, board, channel):
        return (self.current_values[4*board + channel])

    ###########################################################
    ############ Hardware-dependent implementation ############
    #### See ~/Desktop/Luigi/DDS/KRb3DDSAD9959 for details ####
    ###########################################################

    @inlineCallbacks
    # sequence should be a list of dicts
    # [{"address": address, "frequency": frequency}, ..., ]
    def program_frequencies(self, sequence):
        for item in sequence:
            try:
                address = item['address']
                frequency = item['frequency']

                if frequency >= 0 and frequency < self.clk * self.multiplier / 2.0:
                    # Calculate tuning word 
                    tuningword = self.freq2word(float(frequency), self.clk * self.multiplier)
                    ep02, ep01 = self.wordsplit(tuningword)

                    # Get channel select and clock 
                    ep00 = self.cselect(address[0], address[1], self.multiplier, self.vcogain)

                    # Get channel name
                    name = self.channels[4*address[0] + address[1]].name
                    print("{0} MHz written to {1}".format(frequency, name))

                    # Update current_values array
                    self.current_values[4*address[0] + address[1]] = {"name": name, "frequency": frequency}

                    # Set wire ins to FPGA
                    yield self.connection.set_wire_in(0x00, ep00)
                    yield self.connection.set_wire_in(0x01, ep01)
                    yield self.connection.set_wire_in(0x02, ep02)
                    yield self.connection.update_wire_ins()

                    sleep(0.1)
                    # yield sleep(0.001)

                    yield self.connection.set_wire_in(0x00, 0)
                    yield self.connection.update_wire_ins()
                else:
                    print("Channel ({}, {}): Frequency out of range.\n".format(address[0], address[1]))
            
            except Exception as e:
                print(e)

    def freq2word(self, frequency, clock):
        #Convert frequency in MHz to tuning word
        resolution = 2**self.bits
        tuningword = int(frequency*resolution/clock)
        return "{0:032b}".format(tuningword)

    def wordsplit(self, word):
        #Split tuning word for passing to fpga
        return int(word[0:16],2), int(word[16:32],2)

    def cselect(self, dds, channel, multiplier, vcogain):
        #Generate words for channel selection and clock configuration
        x1 = ["0"]*8
        x1[3 - channel] = "1"
        x2 = "{0:05b}".format(multiplier)
        x3 = str(1*vcogain)
        x4 = "{0:02b}".format(dds + 1)
        x = "".join(x1) + x2 + x3 + x4
        return int(x,2)

