from twisted.internet.defer import inlineCallbacks, returnValue

from rf_wrapper import RFWrapper

class MFG2160(RFWrapper):
    timeout = 0.2 # [s]
    @inlineCallbacks
    def initialize(self):
        for command in self.init_commands:
            yield self.connection.write_line(command)

    def get_state(self):
        return True
    
    def set_state(self):
        pass
    
    @inlineCallbacks
    def set_frequency(self, frequency):
        command = 'SOUR3RF:FREQ {}'.format(frequency)
        yield self.connection.write_line(command)

    @inlineCallbacks
    def get_frequency(self):
        yield self.connection.write_line('SOUR3RF:FREQ?')
        ans = yield self.connection.read_lines()
        returnValue(float(ans[0]))

    @inlineCallbacks
    def set_amplitude(self, amplitude):
        command = 'SOUR3RF:AMP {}'.format(amplitude)
        yield self.connection.write_line(command)

    @inlineCallbacks
    def get_amplitude(self):
        yield self.connection.write_line('SOUR3RF:AMP?')
        ans = yield self.connection.read_lines()
        print ans
        returnValue(float(ans[0]))

