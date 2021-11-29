"""
Interface for talking to Arduino + AD9910 hardware.

The hardware and Arduino software are described `here <https://1drv.ms/w/s!AqeccKQeGrL_wEZhytKyrRwIMO9D?e=nobSeE>`_. 

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

import json
from datetime import datetime

# import helpers # helper functions for calculating bytes to transfer
sys.path.append('..')
from server_tools.device_server import DeviceServer

MAX_PROGRAM_LEN = 11
N_PROFILES = 8

class ProgramLine(object):
    """
    Class for validating the data for a line of the program.
    """
    def __init__(self, data):
        try:
            self.mode = data['mode']

            if self.mode == 'single':
                self.frequency = float(data['freq'])
                self.amplitude = float(data['ampl'])
                self.phase = float(data['phase'])

            elif self.mode == 'sweep':
                self.start = float(data['start'])
                self.stop = float(data['stop'])
                self.dt = float(data['dt'])
                self.nsteps = int(data['nsteps'])

            else:
                raise Exception('Invalid mode {} for program line'.format(self.mode))
        except KeyError as e:
            raise Exception('Invalid program input, missing key: {}'.format(e))
        except ValueError as e:
            raise Exception('Invalid program input, bad value: {}'.format(e))
        except Exception as e:
            raise(e)
    
    def __str__(self):
        if self.mode == 'single':
            return json.dumps({'mode': self.mode, 'freq': self.frequency, 'ampl': self.amplitude, 'phase': self.phase})
        elif self.mode == 'sweep':
            return json.dumps({'mode': self.mode, 'start': self.start, 'stop': self.stop, 'dt': self.dt, 'nsteps': self.nsteps})

class Profile(object):
    """
    Class for validating the data for a single profile.
    """
    def __init__(self, data):
        try:
            self.index = int(data['profile'])
            self.frequency = float(data['freq'])
            self.amplitude = float(data['ampl'])
            self.phase = float(data['phase'])
        except KeyError as e:
            raise Exception('Invalid profile input, missing key: {}'.format(e))
        except ValueError as e:
            raise Exception('Invalid profile input, bad value: {}'.format(e))
        except Exception as e:
            raise(e)

    def __str__(self):
        return json.dumps({'profile': self.index, 'freq': self.frequency, 'ampl': self.amplitude, 'phase': self.phase})

class AD9910Server(DeviceServer):
    """
    Server for communicating with AD9910 + Arduino setup.

    The current hardware setup uses an Arduino to program the AD9910 evaluation board over SPI.
    The AD9910 has a set of 8 single-frequency registers (called the "profiles") that can be rapidly and phase-coherently switched via external digital inputs.
    Additionally, the Arduino can hold an array (length < 12) of values (called the "program"), which are advanced by an external trigger input to the Arduino.
    The program also allows for frequency sweeps, which are useful for performing adiabatic rapid passages (ARPs).
    
    Currently, this server assumes this general architecture; however, it should be straightforward to add new hardware implementations (``./devices``) in the future.
    """
    name = '%LABRADNODE%_ad9910'

    @setting(10, "Write data", program_dump='s', profiles_dump='s')
    def write_data(self, c, program_dump, profiles_dump):
        """
        write_data(self, c, program_dump, profiles_dump)
        
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
            program_dump = json.dumps(program)

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
            profiles_dump = json.dumps(profiles)

        Technical note: our TTLs (which drive P0-P2) ring a bit, so changing multiple profile TTLs at the same time may result in an unreliable output.
        In the example above, the profiles are ordered in a Gray encoding, so they can be stepped through in the above order by changing only one of the profile TTLs in each step.
        It is fine to omit unused profiles.

        This method accepts the ``json.dumps``'ed lists since data must be serialized before transmitting over LabRAD.

        Args:
            c: LabRAD context
            program_dump (str): JSON-dumped list of program lines
            profiles_dump (str): JSON-dumped list of profiles
        """

        try:
            name = c['name']
        except KeyError:
            raise Exception('Please select a device first; devices: {}'.format(self.devices.keys()))

        prog = json.loads(program_dump)
        prof = json.loads(profiles_dump)

        if len(prog) > MAX_PROGRAM_LEN:
            raise Exception('Program too long; must be < {} lines'.format(MAX_PROGRAM_LEN))
        if len(prof) > N_PROFILES:
            raise Exception('Too many profile lines set')

        program = [ProgramLine(l) for l in prog]
        # Ensure set to zero at end
        program.append(ProgramLine({"mode": "single", "freq": 0, "ampl": 0, "phase": 0}))

        profiles = [Profile(l) for l in prof]

        dev = self.devices[name]
        yield dev.write_data(program, profiles)

    @setting(11, "Inspect echo", returns='s')
    def inspect_echo(self, c):
        """
        inspect_echo(self, c)
        
        For debugging purposes...
        
        TODO: write me later!

        Args:
            c: LabRAD context
        Returns:
            str: The echoed string from the Arduino
        """
        try:
            name = c['name']
        except KeyError:
            raise Exception('Please select a device first; devices: {}'.format(self.devices.keys()))

        dev = self.devices[name]
        return dev.get_echo()

    @setting(12, "Force trigger")
    def force_trigger(self, c):
        """
        force_trigger(self, c)
    
        Issue trigger to device over serial (instead of external trigger)

        Args:
            c: LabRAD context
        Returns:

        """
        try:
            name = c['name']
        except KeyError:
            raise Exception('Please select a device first; devices: {}'.format(self.devices.keys()))

        dev = self.devices[name]
        return dev.force_trigger()

if __name__ == '__main__':
    from labrad import util
    util.runServer(AD9910Server())
