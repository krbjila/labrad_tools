"""
Provides low-level control of the 4-channel RF synthesizer developed by the JILA shop.

To do:
    * Finish implementing communications using sockets

..
    ### BEGIN NODE INFO
    [info]
    name = synthesizer
    version = 1
    description = server for the JILA 4-channel RF synthesizer
    instancename = %LABRADNODE%_synthesizer
    [startup]
    cmdline = %ANACONDA3% %FILE%
    timeout = 20
    [shutdown]
    message = 987654321
    timeout = 20
    ### END NODE INFO
"""

from math import pi
import sys, os
from labrad.server import LabradServer, setting
sys.path.append("../client_tools")
from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.internet import reactor
from labrad.util import getNodeName
from jsonpickle import loads
import socket

import sys, os
sys.path.append(os.path.dirname(os.path.realpath(__file__)))

import synthesizer_sequences as ss

class SynthesizerServer(LabradServer):
    """Provides low-level control of the 4-channel RF synthesizer developed by the JILA shop."""
    name = '%LABRADNODE%_synthesizer'

    def __init__(self):
        self.name = '{}_synthesizer'.format(getNodeName())
        super(SynthesizerServer, self).__init__()

    def initServer(self):
        """
        initServer(self)
        
        Called by LabRAD when server is started. Connects to the synthesizer using the socket library.
        """
        timeout = 1.02
        port = 804
        host = '192.168.7.179'
        self.dest = (host, int(port))
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, 0)
        self.sock.settimeout(timeout)

    @staticmethod
    def f_to_ftw(f):
        """
        f_to_ftw(f)

        Converts a frequency in Hertz to the format required for programming the synthesizer

        Args:
            f (float): The frequency in Hertz

        Raises:
            ValueError: Raises an error if the frequency is less than zero or greater than the maximum frequency

        Returns:
            int: The 32-bit unsigned integer corresponding to f
        """
        F_MAX = 307.2E6
        F_BITS = 32
        if f < 0 or f > F_MAX * (2**F_BITS - 1) / 2**F_BITS:
            raise ValueError("Frequency of {} Hz outside valid range of 0 to {} Hz".format(f, F_MAX))
        f_int = round((f/F_MAX)*(2**F_BITS - 1))
        return f_int

    @staticmethod
    def a_to_atw(a):
        """
        a_to_atw(a)

        Converts an amplitude to the format required for programming the synthesizer

        Args:
            a (float): The amplitude, relative to full scale

        Raises:
            ValueError: Raises an error if the amplitude is less than zero or greater than one

        Returns:
            int: The 16-bit unsigned integer corresponding to a
        """
        A_BITS = 16
        if a < 0 or a > 1:
            raise ValueError("Amplitude of {} outside valid range of 0 to 1".format(a))
        a_int = round(a*(2**A_BITS-1))
        return a_int

    @staticmethod
    def t_to_timestamp(t):
        """
        t_to_timestamp(t)

        Converts a time to the format required for programming the synthesizer

        Args:
            t (float): The time, in seconds

        Raises:
            ValueError: Raises an error if the time is less than zero or greater than 27.962 seconds

        Returns:
            int: The 48-bit unsigned integer corresponting to t
        """
        T_MIN = 1/153.6E6
        T_BITS = 48
        T_MAX = T_MIN * (2**T_BITS - 1)
        if t < 0 or t > T_MAX:
            raise ValueError("Time step of {} s outside valid range of 0 to {} s".format(t, T_MAX))
        t_int = round(t / T_MIN)
        return t_int

    @staticmethod
    def phase_to_ptw(phi):
        """
        phase_to_ptw(phi)

        Converts a phase to the format required for programming the synthesizer

        Args:
            phi (float): The phase in radians.

        Returns:
            int: The 12-bit unsigned integer corresponting to phi
        """
        P_BITS = 12
        a_int = round((phi % (2*pi))/(2*pi)*(2**P_BITS-1))
        return a_int

    @staticmethod
    def compile_timestamp(channel, address, timestamp, phase_update, phase, amplitude, frequency, wait_for_trigger=False, digital_out=[False]*7):
        """
        compile_timestamp(self, channel, address, timestamp, phase_update, ptw, atw, ftw)

        Compiles a timestamp into a binary command which can be written to the synthesizer

        Args:
            channel (int): The channel to set. Must be between 0 and 3.
            address (int): The address of the timestep
            timestamp (int): The time of the timestamp (in s).
            phase_update (int): Whether to update the phase. 0 to not change phase, 1 to set absolute phase, 2 to increment phase.
            phase (int): The phase (in radians) to set
            amplitude (int): The amplitude (relative to full scale) to set
            frequency (int): The frequency (in Hz) to set
            wait_for_trigger (bool): Whether to wait for a trigger. Defaults to False.
            digital_out ([bool]): A list of 7 booleans, corresponding to whether each channel should be turned on. Defaults to [False]*7, in which case the digital outputs are off.

        Returns:
            List[ByteArray]: The messages to send to the synthesizer that represent the timestamp.
        """

        N_CHANNELS = 4
        N_ADDRESSES = 2**14
        N_DIGITAL = 7

        if channel >= N_CHANNELS or channel < 0 or not isinstance(channel, int):
            raise ValueError("Channel number {} must be an integer between 0 and {}.".format(channel, N_CHANNELS - 1))

        if address >= N_ADDRESSES or address < 0 or not isinstance(address, int):
            raise ValueError("Address {} must be an integer between 0 and {}.".format(address, N_ADDRESSES - 1))

        if phase_update != 0 and phase_update != 1 and phase_update != 2:
            raise ValueError("phase_update {} must be 0, 1, or 2.".format(phase_update))

        buffers = []
        for i in range(4):
            b = bytearray(8)
            b[0] = 0xA1 # Start bits
            b[1] = 2**4 * i + channel # Memory, channel
            b[2:4] = address.to_bytes(2, "big")
            buffers.append(b)

        # Timestamp & digital outputs
        ttw = SynthesizerServer.t_to_timestamp(timestamp)
        for i in range(N_DIGITAL):
            ttw += digital_out[i] * 2**(56+i)
        ttw = ttw.to_bytes(8, "big")


        buffers[0][4:] = ttw[4:]
        buffers[1][4:] = ttw[:4]
        buffers[1][5] += wait_for_trigger

        # Frequency
        ftw = SynthesizerServer.f_to_ftw(frequency)
        buffers[2][4:] = ftw.to_bytes(4, "big")

        # Phase
        ptw = SynthesizerServer.phase_to_ptw(phase)
        buffers[3][4:6] = ptw.to_bytes(2, "big")
        if phase_update == 1: # Absolute phase update
            buffers[3][4] += 2**4
        elif phase_update == 2: # Relative phase update
            buffers[3][4] += 2**5

        # Amplitude
        atw = SynthesizerServer.a_to_atw(amplitude)
        buffers[3][6:] = atw.to_bytes(2, "big")

        return buffers

    @inlineCallbacks
    @setting(3)
    def trigger(self, c):
        """
        trigger(self)

        Triggers the synthesizer

        Args:
            c: The LabRAD context.
        """
        buffer = bytearray.fromhex(f"A200")
        yield self.sock.sendto(buffer, self.dest)
        print("Synthesizer triggered.")


    @inlineCallbacks
    @setting(4, reset_outputs='b')
    def reset(self, c, reset_outputs=False):
        """
        reset(self)

        Resets the synthesizer

        Args:
            c: The LabRAD context.
            reset_outputs: Whether to zero the outputs or just the sequencer
        """
        if reset_outputs:
            buffer = bytearray.fromhex(f"A400")
        else:
            buffer = bytearray.fromhex(f"A300")
        yield self.sock.sendto(buffer, self.dest)
        print("Synthesizer reset.")

    def _write_timestamps(self, timestamps, channel, verbose=False):
        """
            _write_timestamps(self, timestamps, channel, verbose=False)

            Programs the synthesizer with a list of timestamps.

        Args:
            timestamps (list of dictionaries): Each timestamp must contain fields:
                *timestamp: The time in seconds before the update
                *phase_update: 0 to preserve phase, 1 to set absolute phase, 2 to set relative phase
                *phase: The phase in radians
                *amplitude: The amplitude (between 0 and 1) relative to full scale
                *frequency: The frequency (between 0 and 307.2 MHz) in Hz
            channel (int): An integer between 0 and 3 determining the channel to program
            verbose (bool, optional): Whether to print the messages sent to the synthesizer. Defaults to False.
        """
        buffers = []
        for i, s in enumerate(timestamps):
            timestamp = s["timestamp"]
            phase_update = s["phase_update"]
            phase = s["phase"]
            address = i
            amplitude = s["amplitude"]
            frequency = s["frequency"]
            wait_for_trigger = bool(s["wait_for_trigger"])
            digital_out = s["digital_out"]
            buffers += SynthesizerServer.compile_timestamp(channel, address, timestamp, phase_update, phase, amplitude, frequency, wait_for_trigger, digital_out)
        print("Writing Channel {}.".format(channel))
        for b in buffers:
            if verbose:
                print(b.hex())
            self.sock.sendto(b, self.dest)

    @inlineCallbacks
    @setting(5, timestamps='s', compile='b', verbose='b')
    def write_timestamps(self, c, timestamps, compile=False, verbose=False):
        """
        write_timestamps(self, c, timestamps, compile=False, verbose=False)

        Writes timestamps from a JSON-formatted string. See :meth:`write_timestamps` for specification.

        Args:
            c: The LabRAD context. Not used.
            timestamps (str): A JSON-formatted string containing a dictionary (keys: channels, values: sequences) of lists of dictionaries, each of which is a timestamp.
        """
        timestamps = loads(timestamps, keys=True)
        if compile:
            timestamps = loads(ss.compile_sequence(timestamps)[0], keys=True)
        for channel, ts in timestamps.items():
            yield self._write_timestamps(ts, int(channel), verbose)

if __name__ == '__main__':
    from labrad import util
    util.runServer(SynthesizerServer())