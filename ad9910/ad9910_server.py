"""
### BEGIN NODE INFO
[info]
name = ad9910
version = 1.1
description = 
instancename = %LABRADNODE%_ad9910

[startup]
cmdline = %PYTHON% %FILE%
timeout = 20

[shutdown]
message = 987654321
timeout = 20
### END NODE INFO
"""
import sys

from time import sleep

from labrad.server import LabradServer, setting, Signal
from twisted.internet.defer import inlineCallbacks, returnValue
from serial import Serial
import serial.tools.list_ports

import json
from datetime import datetime

import helpers # helper functions for calculating bytes to transfer

sys.path.append('../')
from server_tools.hardware_interface_server import HardwareInterfaceServer


ad9910_address = 'COM4' # address for AD9910 arduino


class AD9910Server(HardwareInterfaceServer):
    """Provides access to hardware's serial interface """
    name = '%LABRADNODE%_ad9910'

    def refresh_available_interfaces(self):
        addresses = [cp[0] for cp in serial.tools.list_ports.comports()]
        
        for address in addresses:
            if address in self.interfaces.keys():
                try:
                    self.interfaces[address].isOpen()
                except:
                    print '{} unavailable'.format(address)
                    del self.interfaces[address]
            else:
                try:
                    if address == ad9910_address:
                        ser = Serial(address, 4800, timeout=2)
                        ser.close()
                        self.interfaces[address] = ser
                        print '{} available'.format(address)
                except:
                    pass
        
    def get_interface(self, c, suppress_output=False):
        interface = super(AD9910Server, self).get_interface(c)
        if not interface.isOpen():
            interface.open()
        self.verify_interface(c, suppress_output)
        return interface
    
    def verify_interface(self, c, suppress_output=False):
        ser = super(AD9910Server, self).get_interface(c)
        if not ser.isOpen():
            ser.open()
        ser.write('cxn?\n')
        ser.flush()
        response = ser.readline()
        if response == "ad9910\n":
            if not suppress_output:
                print "verified as ad9910"
        else:
            ser.close()
            del self.interfaces[ser]

    @setting(2, returns='b')
    def disconnect(self, c):
        self.refresh_available_interfaces()
        if c['address'] not in self.interfaces:
            raise Exception(c['address'] + 'is unavailable')
        interface = self.get_interface(c)
        interface.close()
        del c['address']
        return True

    def createProgramString(self, line, data_type, byte_string):
        addr = "0x{0:02X},".format(line)
        try:
            data_type = int(data_type)
        except ValueError:
            data_type = int(helpers.tx_types_dictionary[data_type])
        data_type = "0x{0:02X},".format(data_type)
        return addr + data_type + byte_string + "\n"

    def createProfileString(self, profile, byte_string):
        data_type = "0x00,"
        addr = "0x{0:02X},".format(profile + 12)
        return addr + data_type + byte_string + "\n"

    def compileProgramStrings(self, program_array):
        length = len(program_array)
        if length > 12: # truncate program to 12 if longer
            length = 12

        program = ""
        for i in range(0, length):
            line = program_array[i]
            line_str = ""
            if line['mode'] == 'single':
                ampl_str = helpers.calcAMPL(line['ampl'])
                pow_str = helpers.calcPOW(line['phase'])
                ftw_str = helpers.calcFTW(line['freq'])
                line_str = self.createProgramString(i, 'single', ampl_str + pow_str + ftw_str) + "\n"
            elif line['mode'] == 'sweep':
                if 'nsteps' in line:
                    sweep_dict = helpers.calcRampParameters(line['start'], line['stop'], line['dt'], line['nsteps'])
                else:
                    sweep_dict = helpers.calcRampParameters(line['start'], line['stop'], line['dt'])

                # Create ramp limits string (DDS reg 0x0B)
                limits_string = helpers.calcFTW(sweep_dict['upper']) + helpers.calcFTW(sweep_dict['lower'])
                line_str = self.createProgramString(i, 'drLimits', limits_string) + "\n"

                # Create frequency step size string (DDS reg 0x0C)
                steps_string = helpers.calcFTW(sweep_dict['n_step']) + helpers.calcFTW(sweep_dict['p_step'])
                line_str += self.createProgramString(i, 'drStepSize', steps_string) + "\n"

                # Create ramp rate string (DDS reg 0x0D)
                ramp_rate_str = helpers.calcStepInterval(sweep_dict['n_interval']) + helpers.calcStepInterval(sweep_dict['p_interval'])
                line_str += self.createProgramString(i, 'drRate', ramp_rate_str) + "\n"

                # Create instruction string to tell the DDS whether the ramp should have a positive or negative slope
                if sweep_dict['slope'] == 1:
                    line_str += self.createProgramString(i, 'sweepInvert', "0x00,") + "\n"
                else:
                    line_str += self.createProgramString(i, 'sweepInvert', "0x01,") + "\n"
            program += line_str
        return program

    def compileProfileStrings(self, profiles_array):
        length = len(profiles_array)
        # If too many profiles, just keep first 8
        if length > 8:
            length = 8

        profile_string = ""
        for i in range(0, length):
            line = profiles_array[i]
            ftw_str = helpers.calcFTW(line['freq'])
            ampl_str = helpers.calcAMPL(line['ampl'])
            pow_str = helpers.calcPOW(line['phase'])
            line_str = self.createProfileString(line['profile'], ampl_str + pow_str + ftw_str) + "\n"
            profile_string += line_str
        return profile_string

    def writeProgramAndProfiles(self, ser_interface, program_string, profile_string):
        ser_interface.write(program_string)
        ser_interface.flush()
        ser_interface.write(profile_string)
        ser_interface.flush()
        ser_interface.write("Done\n")

    def getEcho(self, ser_interface, program_array):
        num_lines = 2 * 8

        length = len(program_array)
        if length > 12:
            length = 12
        for i in range(0, length):
            line = program_array[i]
            if line['mode'] == 'single':
                num_lines += 2
            elif line['mode'] == 'sweep':
                num_lines += 4
        echo = []
        for i in range(0, num_lines):
            echo.append(ser_interface.readline())
        echo_str = ""
        for s in echo:
            echo_str += s
        return echo_str
    
    @setting(3, 'Parse JSON Strings And Update', prog_dump='s', prof_dump='s', suppress_output='b')
    def parseJSONStringsAndProgram(self, c, prog_dump, prof_dump, suppress_output=False):
        interface = self.get_interface(c, suppress_output)

        prog = json.loads(prog_dump)
        program = self.compileProgramStrings(prog)
        profiles = self.compileProfileStrings(json.loads(prof_dump))

        self.writeProgramAndProfiles(interface, program, profiles)

        echo = self.getEcho(interface, prog)
        if not suppress_output:
            print echo
            print "updated " + datetime.now().strftime('%Y-%m-%d %H:%M:%S')


__server__ = AD9910Server()

if __name__ == '__main__':
    from labrad import util
    util.runServer(__server__)
