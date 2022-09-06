"""
Provides low-level control of the 4-channel RF synthesizer developed by the JILA shop.

..
    ### BEGIN NODE INFO
    [info]
    name = synthesizer
    version = 1
    description = server for the JILA 4-channel RF synthesizer
    instancename = %LABRADNODE%_synthesizer
    [startup]
    cmdline = %PYTHON3% %FILE%
    timeout = 20
    [shutdown]
    message = 987654321
    timeout = 20
    ### END NODE INFO
"""

from math import pi
import sys
from labrad.server import LabradServer, setting
sys.path.append("../client_tools")
from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.internet import reactor
from labrad.util import getNodeName
import struct
from json import loads

class SynthesizerServer(LabradServer):
    """Provides low-level control of the 4-channel RF synthesizer developed by the JILA shop."""
    name = '%LABRADNODE%_synthesizer'

    def __init__(self):
        self.name = '{}_synthesizer'.format(getNodeName())
        super(SynthesizerServer, self).__init__()

    @inlineCallbacks
    def initServer(self):
        """
        initServer(self)
        
        Called by LabRAD when server is started. Connects to :class:`usb.USB_server`.
        """
        self.USB_server_name = '{}_usb'.format(getNodeName())
        self.USB = yield self.client.servers[self.USB_server_name]
        self.USB.select_interface("COM6")
        self.USB.termination('', '')
        self.USB.baudrate(115200)
        self.USB.timeout(0.1)
        self.uart = self.USB

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
        f_int = round(F_MAX*f/2**F_BITS)
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
            int: The 32-bit unsigned integer corresponting to t
        """
        T_MIN = 1/153.6E6
        T_BITS = 32
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

        Raises:
            ValueError: Raises an error if the phase is less than zero or greater than 2 pi

        Returns:
            int: The 12-bit unsigned integer corresponting to phi
        """
        P_BITS = 12
        if phi < 0 or phi >= 2*pi:
            raise ValueError("Phase of {} outside valid range of 0 to 2 pi".format(phi))
        a_int = round(phi/(2*pi)*(2**P_BITS-1))
        return a_int

    @staticmethod
    def channels_to_channel(channels):
        """
        channels_to_channel(channels)

        Args:
            channels (int or list of ints): The channels to set

        Raises:
            ValueError: Raises an error if the channel is not an integer or a list of integers between 0 and 3

        Returns:
            int: The 4-bit integer corresponding to channels
        """
        N_CHANNELS = 4
        if isinstance(channels, int):
            channels = [channels]
        if len(channels) == 0:
            raise ValueError("Must specify at least one channel")
        channel = 0
        for c in set(channels):
            if c >= N_CHANNELS or c < 0 or not isinstance(c, int):
                raise ValueError("Channel number {} must be an integer between 0 and {}.".format(c, N_CHANNELS - 1))
            channel += 2**(c-1)
        return channel

    def write_timestamp(self, channel, address, timestamp, phase_update, ptw, atw, ftw, verbose=False):
        """
        write_timestamp(self, channel, address, timestamp, phase_update, ptw, atw, ftw, verbose=False)

        Args:
            channel (int): The channels to set, as generated by meth:channels_to_channel
            address (int): The address of the timestep
            timestamp (int): The time of the timestamp, as generated by meth:t_to_timestamp
            phase_update (bool): Whether to update the phase
            ptw (int): The phase to set, as generated by meth:phase_to_ptw
            atw (int): The amplitude to set, as generated by meth:a_to_atw
            ftw (int): The frequency to set, as generated by meth:f_to_ftw
            verbose (bool, optional): Whether to print the data getting sent to the synthesizer. Defaults to False.
        """
        if verbose: print("New timestamp")
        phase = ptw
        if(phase_update): phase += 0x1000 # set update bit
        self.uart.write(struct.pack('>B', 0xA1))
        if verbose: print("fifo trans", struct.pack('>B', 0xA1))

        self.uart.write(struct.pack('>B', channel))
        if verbose: print("channel", struct.pack('>B', channel))

        self.uart.write(struct.pack('>H', address))
        if verbose: print("address", struct.pack('>H', address))

        self.uart.write(struct.pack('>I', timestamp))
        if verbose: print("time", struct.pack('>I', timestamp))

        self.uart.write(struct.pack('>H', phase))
        if verbose: print("phase", struct.pack('>H', phase))

        self.uart.write(struct.pack('>H', atw))
        if verbose: print("atw", struct.pack('>H', atw))

        self.uart.write(struct.pack('>I', ftw))
        if verbose: print("ftw", struct.pack('>I', ftw))

        self.uart.write(struct.pack('>B', 0x00))
        if verbose: print("terminator", struct.pack('>B', 0x00))

        if verbose: print("End timestamp")

        # the uart buffer is only 16 bytes deep, so we need to wait until all data is written after every word
        self.uart.flush()

    @setting(3)
    def trigger(self, c=None):
        """
        trigger(self)

        Triggers the synthesizer

        Args:
            c (optional): The LabRAD context. Defaults to None.
        """
        msg = bytearray(2)
        msg[0] = 0xA2
        msg[1] = 0x00
        self.uart.write(msg)
        # the uart buffer is only 16 bytes deep, so we need to wait until all data is written after every word
        self.uart.flush()

    @setting(4)
    def reset(self, c=None):
        """
        reset(self)

        Resets the synthesizer

        Args:
            c (optional): The LabRAD context. Defaults to None.
        """
        msg = bytearray(2)
        msg[0] = 0xA3
        msg[1] = 0x00
        self.uart.write(msg)
        # the uart buffer is only 16 bytes deep, so we need to wait until all data is written after every word
        self.uart.flush()

    def write_timestamps(self, timestamps):
        """
            write_timestamps(self, timestamps)

            Programs the synthesizer with a list of timestamps.

        Args:
            timestamps (list of dictionaries): Each timestamp must contain fields:
                *channel: A number or list of numbers (between 0 and 3) corresponding to the channels to set
                *timestamp: The time in seconds before the update
                *phase_update: A boolean whether the phase is set or not
                *phase: The phase (between 0 and 2 pi) to set. Only used if phase_update is True.
                *amplitude: The amplitude (between 0 and 1) relative to full scale
                *frequency: The frequency (between 0 and 307.2 MHz) in Hz
                
        """
        for address, s in enumerate(timestamps):
            channel = SynthesizerServer.channels_to_channel(s.channels)
            timestamp = SynthesizerServer.t_to_timestamp(s.timestamp)
            phase_update = bool(s.phase_update)
            ptw = SynthesizerServer.phase_to_ptw(s.phase)
            atw = SynthesizerServer.a_to_atw(s.amplitude)
            ftw = SynthesizerServer.f_to_ftw(s.frequency)
            self.write_timestamp(channel, address, timestamp, phase_update, ptw, atw, ftw)

    @setting(5, timestamps='s')
    def write_timestamps(self, c, timestamps):
        """
        write_timestamps(self, c, timestamps)

        Writes timestamps from a JSON-formatted string. See meth:write_timestamps for specification.

        Args:
            c: The LabRAD context. Not used.
            timestamps (str): A JSON-formatted string containing a list of dictionaries of timestamps.
        """
        self.write_timestamps(loads(timestamps))

if __name__ == '__main__':
    from labrad import util
    util.runServer(SynthesizerServer())