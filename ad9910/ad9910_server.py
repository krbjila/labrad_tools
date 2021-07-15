"""
Interface for talking to Arduino + AD9910 hardware.

TODO: Add a link or something here to document the Arduino + AD9910 setup

..
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
sys.path.append('..')
from server_tools.hardware_interface_server import HardwareInterfaceServer

ad9910_address = 'COM4' # address for AD9910 arduino

ADDRESSES = {
    'N=1': 'COM4',
    'N=2': 'COM10',
}

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
                    print('{} unavailable'.format(address))
                    del self.interfaces[address]
            else:
                try:
                    if address in ADDRESSES.values():
                        ser = Serial(address, 4800, timeout=2)
                        ser.open()
                        verified = self.verify_interface(ser)

                        if verified:
                            name = ADDRESSES[address]
                            self.interfaces[name] = ser
                            print('{} available'.format(address))
                        else:
                            ser.close()
                except:
                    pass
        
    # def get_interface(self, c, suppress_output=False):
    #     interface = super(AD9910Server, self).get_interface(c)
    #     if not interface.isOpen():
    #         interface.open()
    #     self.verify_interface(c, suppress_output)
    #     return interface
    
    # def verify_interface(self, c, suppress_output=False):
    #     ser = super(AD9910Server, self).get_interface(c)
    #     if not ser.isOpen():
    #         ser.open()
    #     ser.write('cxn?\n')
    #     ser.flush()
    #     response = ser.readline()
    #     if response == "ad9910\n":
    #         if not suppress_output:
    #             print("verified as ad9910")
    #     else:
    #         ser.close()
    #         del self.interfaces[ser]

    def verify_interface(self, device):
        if not device.isOpen():
            device.open()
        device.write('cxn?\n')
        device.flush()
        response = device.readline()
        return response == "ad9910\n"

    def stopServer(self):
        for k in self.interfaces.keys():
            try:
                dev = self.interfaces.pop(k)
                dev.close()
            except Exception as e:
                print(e)
        return super(AD9910Server, self).stopServer()

    # @setting(2, returns='b')
    # def disconnect(self, c):
    #     self.refresh_available_interfaces()
    #     if c['address'] not in self.interfaces:
    #         raise Exception(c['address'] + 'is unavailable')
    #     interface = self.get_interface(c)
    #     interface.close()
    #     del c['address']
    #     return True

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
        """
        parseJSONStringsAndProgram(self, c, prog_dump, prof_dump, suppress_output=False)
        
        Takes JSON-dumped program and profile strings and send them to the Arduino.

        The "program" is a list of output settings that are programmed sequentially to the DDS (stepped through by the trigger input to the Arduino).
        Each program line can be a single tone:::

            line = {"mode": "single", "freq": 100, "ampl": 0, "phase": 0}

        or a sweep:::
    
            line = {"mode": "sweep", "start": 10, "stop": 1, "dt": 10, "nsteps": 1000}

        Frequencies are specified in MHz, amplitudes in dB relative to full scale, phases in degrees, and times in ms.
        The single tone setting above corresponds to a 100 MHz tone with full amplitude and no phase offset.
        The sweep above is a 10 ms long sweep from 10 MHz to 1 MHz composed of 1000 frequency steps.

        Here is an example program list, similar to the one we use for doing the K state preparation:::
        
            program = [
                {"mode": "sweep", "start": 10.5, "stop": 7.5, "dt": 70, "nsteps": 10000},
                {"mode": "single", "freq": 80, "ampl": 0, "phase": 0},
                {"mode": "single", "freq": 0, "ampl": 0, "phase": 0},
            ]
            prog_dump = json.dumps(program)

        The profiles are single tone settings that can be rapidly (and phase-coherently) switched using the P0, P1, and P2 digital inputs on the DDS.
        The index of the active profile is given by interpreting the list of bits [P2, P1, P0] as an unsigned int
        (so [P2, P1, P0] = [HIGH, LOW, LOW] is profile 4, [P2, P1, P0] = [LOW, HIGH, LOW] is profile 2, etc.).

        Here is an example profiles list:::
        
            profiles = [
                # Profile 0 is reserved (used for executing the program list)
                {'profile': 0, 'freq': 0, 'ampl': 0, 'phase': 0},

                # Setup some pulse sequence at 120 MHz
                {'profile': 1, 'freq': 120, 'ampl': 0, 'phase': 0},
                {'profile': 3, 'freq': 120, 'ampl': 0, 'phase': -90},
                {'profile': 2, 'freq': 120, 'ampl': 0, 'phase': 45},
                {'profile': 6, 'freq': 120, 'ampl': 0, 'phase': 135},
                {'profile': 7, 'freq': 120, 'ampl': 0, 'phase': -180},

                # Setup another Ramsey sequence at 220 MHz
                {'profile': 5, 'freq': 220, 'ampl': -10, 'phase': 0},
                {'profile': 4, 'freq': 220, 'ampl': -10, 'phase': 45},
            ]
            prof_dump = json.dumps(profiles)

        Technical note: our TTLs (which drive P0-P2) ring a bit, so changing multiple profile TTLs at the same time may result in an unreliable output.
        In the example above, the profiles are ordered in a Gray encoding, so they can be stepped through in the above order by changing only one of the profile TTLs in each step.
        It is fine (maybe?) to omit unused profiles.

        This method accepts the ``json.dumps``'ed lists since data transmitted through LabRAD needs to be serialized.

        Args:
            c: LabRAD context
            prog_dump (str): JSON-dumped list of program lines
            prof_dump (str): JSON-dumped list of profiles
            suppress_output (bool, optional): Flag to suppress verbose output. Defaults to False.
        """
        interface = self.get_interface(c)

        prog = json.loads(prog_dump)
        program = self.compileProgramStrings(prog)
        profiles = self.compileProfileStrings(json.loads(prof_dump))

        self.writeProgramAndProfiles(interface, program, profiles)

        echo = self.getEcho(interface, prog)
        if not suppress_output:
            print(echo)
            print("updated " + datetime.now().strftime('%Y-%m-%d %H:%M:%S'))


__server__ = AD9910Server()

if __name__ == '__main__':
    from labrad import util
    util.runServer(__server__)
