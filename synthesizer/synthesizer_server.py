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
# from connection import connection
from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.internet import reactor
from labrad.util import getNodeName
import struct

class SynthesizerServer(LabradServer):
    """Provides low-level control of the 4-channel RF synthesizer developed by the JILA shop."""
    name = '%LABRADNODE%_synthesizer'

    def __init__(self):
        self.name = '{}_synthesizer'.format(getNodeName())
        super(SynthesizerServer, self).__init__()
        self.uart = serial.Serial('/dev/ttyUSB2', 115200, timeout=0.1)

    @inlineCallbacks
    def initServer(self):
        """
        initServer(self)
        
        Called by LabRAD when server is started. Connects to :class:`usb.USB_server`.
        """
        self.USB_server_name = '{}_usb'.format(getNodeName())
        self.USB = yield self.client.servers[self.USB_server_name]

    @setting(5, returns='*s')
    def get_devices(self, c):
        """
        get_devices(self, c)

        Lists connected DG800 AWGs. Note that the function connects to each device to check its ID.

        Args:
            c: A LabRAD context (which is passed on to passed to :meth:`select_device`)

        Yields:
            A list of strings corresponding to the IDs of connected DG800 AWGs
        """
        interfaces = yield self.USB.get_interface_list()
        self.devices = []
        for i in interfaces:
            self.select_device(c, i)
            try:
                id = yield self.USB.query('*IDN?')
                if "DG832" in id:
                    self.devices.append(i)
            except Exception as e:
                print("Could not connect to {}".format(i))
                print(e)
        returnValue(self.devices)

    @setting(6, device='s')
    def select_device(self, c, device):
        """
        select_device(self, c, device)
        
        Select a connected DG800 AWG

        Args:
            c: A LabRAD context (not used)
            device (string): The ID of the DG800 AWG to connect to, as returned by :meth:`get_devices`
        """
        self.USB.select_interface(device)

    @staticmethod
    def f_to_ftw(f):
        """_summary_

        Args:
            f (_type_): _description_

        Raises:
            ValueError: _description_

        Returns:
            _type_: _description_
        """
        F_MAX = 307.2E6
        F_BITS = 32
        if f < 0 or f > F_MAX * (2**F_BITS - 1) / 2**F_BITS:
            raise ValueError("Frequency of {} Hz outside valid range of 0 to {} Hz".format(f, F_MAX))
        f_int = round(F_MAX*f/2**F_BITS)
        return f_int

    @staticmethod
    def a_to_atw(a):
        """_summary_

        Args:
            a (_type_): _description_

        Raises:
            ValueError: _description_

        Returns:
            _type_: _description_
        """
        A_BITS = 16
        if a < 0 or a > 1:
            raise ValueError("Amplitude of {} outside valid range of 0 to 1".format(a))
        a_int = round(a*(2**A_BITS-1))
        return a_int

    @staticmethod
    def t_to_timestamp(t):
        """_summary_

        Args:
            t (_type_): _description_

        Raises:
            ValueError: _description_

        Returns:
            _type_: _description_
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
        """_summary_

        Args:
            phi (_type_): _description_

        Raises:
            ValueError: _description_

        Returns:
            _type_: _description_
        """
        P_BITS = 12
        if phi < 0 or phi >= 2*pi:
            raise ValueError("Phase of {} outside valid range of 0 to 2 pi".format(phi))
        a_int = round(phi/(2*pi)*(2**P_BITS-1))
        return a_int

    def write_timestamp(self, channel, address, timestamp, phase_update, ptw, atw, ftw, verbose=False):
        """_summary_

        Args:
            channel (_type_): _description_
            address (_type_): _description_
            timestamp (_type_): _description_
            phase_update (_type_): _description_
            ptw (_type_): _description_
            atw (_type_): _description_
            ftw (_type_): _description_
            verbose (bool, optional): _description_. Defaults to False.
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

        if verbose: print("  End timestamp")

        # the uart buffer is only 16 bytes deep, so we need to wait until all data is written after every word
        self.uart.flush()

    def trigger(self):
        """_summary_
        """
        msg = bytearray(2)
        msg[0] = 0xA2
        msg[1] = 0x00
        self.uart.write(msg)
        # the uart buffer is only 16 bytes deep, so we need to wait until all data is written after every word
        self.uart.flush()

    def reset(self):
        """_summary_
        """
        msg = bytearray(2)
        msg[0] = 0xA3
        msg[1] = 0x00
        self.uart.write(msg)
        # the uart buffer is only 16 bytes deep, so we need to wait until all data is written after every word
        self.uart.flush()

if __name__ == '__main__':
    from labrad import util
    util.runServer(SynthesizerServer())