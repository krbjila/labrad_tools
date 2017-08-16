import labrad.types as T
from twisted.internet.defer import inlineCallbacks, returnValue

def get_instruction_set(address, register, data):
    ins = [58, address, len(data)+1, register] + data
    ins_sum = sum(ins[1:])
    ins_sum_bin = bin(ins_sum)[2:].zfill(8)
    lowest_byte = ins_sum_bin[-8:]
    checksum = int('0b'+str(lowest_byte), 0)
    ins.append(checksum)
    return [chr(i) for i in ins]

class AD9854(object):
    def __init__(self, config):
        self.timeout = .1
        self.baudrate = 4800
        self.init_commands = []
        
        self.freg = int(0x02)
        self.areg = int(0x08)
        self.amplitude_range = (0, 1)
        self.amplitude = 1
        self.state = True
        self.frequency_range=(1e3, 140e6)
        self.sysclk=300e6
        self.update_parameters = ['state', 'frequency', 'amplitude']

        for key, value in config.items():
            setattr(self, key, value)
        self.connection_name = self.servername + ' - ' + self.address
    
    def ftw(self):
        ftw = hex(int(self.frequency*2.**32/self.sysclk))[2:].zfill(8) # 32-bit dac
        return [int('0x'+ftw[i:i+2], 0) for i in range(0, 8, 2)]

    def atw(self):
        atw =  hex(int(self.amplitude*(2**12-1)))[2:].zfill(4)
        return [int('0x'+atw[i:i+2], 0) for i in range(0, 4, 2)] + [0, 0]

    @inlineCallbacks
    def initialize(self):
        yield self.set_frequency(self.frequency)
        yield self.set_amplitude(self.amplitude)
    
    @inlineCallbacks
    def set_state(self, state):
        yield None

    @inlineCallbacks
    def get_state(self):
        yield None
        returnValue(True)

    @inlineCallbacks
    def set_frequency(self, frequency):
        self.frequency = frequency
        for b in get_instruction_set(self.subaddress, self.freg, self.ftw()):
            yield self.connection.write(b)
        ans = yield self.connection.read_line()
        print ans

    @inlineCallbacks
    def get_frequency(self):
        yield None
        returnValue(self.frequency)
        
    @inlineCallbacks
    def set_amplitude(self, amplitude):
        self.amplitude = amplitude
        for b in get_instruction_set(self.subaddress, self.areg, self.atw()):
            yield self.connection.write(b)
        ans = yield self.connection.read_line()

    @inlineCallbacks
    def get_amplitude(self):
        yield None
        returnValue(self.amplitude)

