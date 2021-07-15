import json
from twisted.internet.defer import inlineCallbacks, returnValue
import sys

sys.path.append('../../')
from server_tools.device_server import DeviceWrapper

from time import sleep

tx_types_dictionary = {
    'single': 0,
    'drLimits': 1,
    'drStepSize': 2,
    'drRate': 3,
    'sweepInvert': 4 # send 0 for no invert, 1 for invert
}

SYSCLK = 1000 # MHz

# Returns string of bytes MSB
# In format "byte_3,byte_2,byte_1,byte_0,"
#
# Argument: frequency in MHz
def calc_ftw(freq):
    calc_ftw = int(2**(32) * float(freq) / SYSCLK)
    # Format string MSB first
    hex_str = '{:08X}'.format(calc_ftw)
    res = ""
    for i in range(0, 4):
        res = res + "0x" + hex_str[2*i:(2*i+2)] + ","
    return res

# Returns string of bytes MSB
# in format "byte_1,byte_0,"
#
# Argument: phase in degrees
def calc_pow(phase):
    phase = phase % 360
    calc_pow = int(2**(16) * float(phase) / 360)

    # Format string
    hex_str = '{0:04X}'.format(calc_pow)
    res = ""
    for i in range(0,2):
        res = res + "0x" + hex_str[2*i:(2*i + 2)] + ","
    return res

# Returns string of bytes MSB
# in format "byte_1,byte_0,"
#
# Argument: relative amplitude in dB relative to full scale
# Range is 0 to -80 dB
def calc_ampl(ampl):
    # Upper limit is 0 dB
    if ampl >= 0:
        return "0x3F,0xFF,"
    # Lower limit is -80 dB
    elif ampl < -80:
        ampl = -80

    AMPL = int(2**(14) * pow(10, float(ampl)/20))
    hex_str = '{0:04X}'.format(AMPL)
    res = ""
    for i in range(0,2):
        res = res + "0x" + hex_str[2*i:(2*i + 2)] + ","
    return res

# Returns string of bytes MSB
# in format "byte_1,byte_0,"
#
# Argument: step interval in microseconds
def calc_step_interval(interval):
    min_interval = float(4) / SYSCLK
    max_interval = (2**(16) - 1) * min_interval
    if (interval < min_interval):
        interval = min_interval
    elif (interval > max_interval):
        interval = max_interval

    intW = int(interval / min_interval)
    # Format string
    hex_str = '{0:04X}'.format(intW)
    res = ""
    for i in range(0,2):
        res = res + "0x" + hex_str[2*i:(2*i + 2)] + ","
    return res

# Calculates ramp parameters
# Input:
#     start: start frequency in MHz
#    stop: stop frequency in MHz
#    dt: duration in milliseconds
#    nsteps (optional): number of steps in sweep, default=1000
#
# Returns: Dictionary with items:
#    upper: upper limit frequency in MHz
#    lower: lower limit frequency in MHz
#    slope: slope polarity (+1 for positive ramp, -1 for negative ramp)
#    interval: step interval for accumulator in microseconds
#    step: frequency change per step in MHz
def calc_ramp_parameters(start, stop, dt, nsteps=1000):
    slope = 0
    if start <= stop:
        slope = 1
        lower = start
        upper = stop
    else:
        slope = -1
        lower = stop
        upper = start

    # dt is given in ms
    # Convert to microseconds
    # To get dt per step, divide by nsteps
    # This is step interval in microseconds
    dt_each = 1000 * float(dt) / nsteps
    df_each = float(upper - lower) / nsteps

    # DRG automatically starts from lower limit
    # If slope is negative, need to do something fancy
    if slope == 1:
        p_interval = dt_each
        n_interval = 0 # minimum step interval
        p_step = df_each
        n_step = df_each
    elif slope == -1:
        p_interval = 0 # minimum step interval; quickly sweep up to upper limit
        n_interval = dt_each
        p_step = float(df_each) * nsteps # positive step size is the whole sweep interval
        n_step = df_each
    return {'upper': upper, 'lower': lower, 'slope': slope, 'p_interval': p_interval, 'n_interval': n_interval, 'p_step': p_step, 'n_step': n_step}


def create_program_string(line, data_type, byte_string):
    addr = "0x{0:02X},".format(line)
    try:
        data_type = int(data_type)
    except ValueError:
        data_type = int(tx_types_dictionary[data_type])
    data_type = "0x{0:02X},".format(data_type)
    return addr + data_type + byte_string + "\n"

def create_profile_string(profile, byte_string):
    data_type = "0x00,"
    addr = "0x{0:02X},".format(profile + 12)
    return addr + data_type + byte_string + "\n"

def compile_program_strings(program_array):
    length = len(program_array)
    if length > 12: # truncate program to 12 if longer
        length = 12

    program = ""
    for i in range(0, length):
        line = program_array[i]
        line_str = ""
        if line['mode'] == 'single':
            ampl_str = calc_ampl(line['ampl'])
            pow_str = calc_pow(line['phase'])
            ftw_str = calc_ftw(line['freq'])
            line_str = create_program_string(i, 'single', ampl_str + pow_str + ftw_str) + "\n"
        elif line['mode'] == 'sweep':
            if 'nsteps' in line:
                sweep_dict = calc_ramp_parameters(line['start'], line['stop'], line['dt'], line['nsteps'])
            else:
                sweep_dict = calc_ramp_parameters(line['start'], line['stop'], line['dt'])

            # Create ramp limits string (DDS reg 0x0B)
            limits_string = calc_ftw(sweep_dict['upper']) + calc_ftw(sweep_dict['lower'])
            line_str = create_program_string(i, 'drLimits', limits_string) + "\n"

            # Create frequency step size string (DDS reg 0x0C)
            steps_string = calc_ftw(sweep_dict['n_step']) + calc_ftw(sweep_dict['p_step'])
            line_str += create_program_string(i, 'drStepSize', steps_string) + "\n"

            # Create ramp rate string (DDS reg 0x0D)
            ramp_rate_str = calc_step_interval(sweep_dict['n_interval']) + calc_step_interval(sweep_dict['p_interval'])
            line_str += create_program_string(i, 'drRate', ramp_rate_str) + "\n"

            # Create instruction string to tell the DDS whether the ramp should have a positive or negative slope
            if sweep_dict['slope'] == 1:
                line_str += create_program_string(i, 'sweepInvert', "0x00,") + "\n"
            else:
                line_str += create_program_string(i, 'sweepInvert', "0x01,") + "\n"
        program += line_str
    return program

def compile_profile_strings(profiles_array):
    length = len(profiles_array)
    # If too many profiles, just keep first 8
    if length > 8:
        length = 8

    profile_string = ""
    for i in range(0, length):
        line = profiles_array[i]
        ftw_str = calc_ftw(line['freq'])
        ampl_str = calc_ampl(line['ampl'])
        pow_str = calc_pow(line['phase'])
        line_str = create_profile_string(line['profile'], ampl_str + pow_str + ftw_str) + "\n"
        profile_string += line_str
    return profile_string

class Arduino(DeviceWrapper):
    def __init__(self, config):
        """ defaults """
        self.program = []
        self.profiles = []
        self.echo = ""

        """ non-defaults"""
        for key, value in config.items():
            setattr(self, key, value)
        super(Arduino, self).__init__({})

    @inlineCallbacks
    def verify_interface(self):
        yield self.connection.write(b'cxn?\n')
        response = yield self.connection.read_line()
        returnValue(response == 'ad9910')

    @inlineCallbacks
    def initialize(self):
        verified = yield self.verify_interface()
        if not verified:
            raise Exception("Could not verify {} as ad9910\n".format(self.address))

    @inlineCallbacks
    def write_data(self, program, profiles):
        self.program = program
        self.profiles = profiles

        program_string = compile_program_strings(program)
        profile_string = compile_profile_strings(profiles)

        yield self.connection.write(program_string)
        yield self.connection.write(profile_string)
        yield self.connection.write("Done\n")
        self.echo = yield self.read_echo(self.program)

    def get_echo(self):
        return self.echo

    @inlineCallbacks
    def read_echo(self, program_array):
        num_lines = 2 * 8

        length = len(program_array)
        if length > 12:
            length = 12
        for line in program_array[0:length]:
            if line['mode'] == 'single':
                num_lines += 2
            elif line['mode'] == 'sweep':
                num_lines += 4

        echo = ''
        for _ in range(0, num_lines):
            s = yield self.connection.read_line()
            echo += s + '\n'
        returnValue(echo)

    


    
