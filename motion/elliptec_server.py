"""
Allows control of Thorlabs elliptec stages.

..
    ### BEGIN NODE INFO
    [info]
    name = elliptec
    version = 1
    description = server for Thorlabs elliptec stages
    instancename = %LABRADNODE%_elliptec

    [startup]
    cmdline = %PYTHON% %FILE%
    timeout = 20

    [shutdown]
    message = 987654321
    timeout = 20
    ### END NODE INFO
"""

import sys
from datetime import datetime
from labrad.server import LabradServer, setting

from pathlib import Path
sys.path.append([str(i) for i in Path(__file__).parents if str(i).endswith("labrad_tools")][0])
from server_tools.hardware_interface_server import HardwareInterfaceServer

from labrad.util import getNodeName
from twisted.internet.defer import inlineCallbacks, returnValue
import json

def twos_complement(hexstr,bits):
    """
    twos_complement(hexstr,bits)

    Converts a hex string of a two's complement number to an integer

    Args:
        hexstr (str): The number in hex
        bits (int): The number of bits in hexstr

    Returns:
        int: An integer containing the number
    """
    value = int(hexstr,16)
    if value & (1 << (bits-1)):
        value -= 1 << bits
    return value

def to_hex(x, bits):
    """
    to_hex(x, bits)

    Converts an integer to two's complement hex

    Args:
        x (int): A number
        bits (int): The number of bits in the output number

    Returns:
        str: A hex string representing x in two's complement
    """
    return hex((1 << bits) + x)[3:]


class elliptecServer(HardwareInterfaceServer):
    """Provides access to Thorlabs elliptec stages."""
    name = '%LABRADNODE%_elliptec'

    TICKS_PER_MM = 1024
    N_CHANNELS = 1
    STATUS_DICT = {
        '00': 'OK',
        '01': 'Communication time out',
        '02': 'Mechanical time out',
        '03': 'Command error',
        '04': 'Value out of range',
        '05': 'Module isolated',
        '06': 'Module out of isolation',
        '07': 'Initializing error',
        '08': 'Thermal error',
        '09': 'Busy',
        '10': 'Sensor error',
        '11': 'Motor error',
        '12': 'Out of range',
        '13': 'Over current error'
    }

    def __init__(self):
        self.serial_server_name = '{}_serial'.format(getNodeName())
        LabradServer.__init__(self)
    
    @inlineCallbacks
    def initServer(self):
        """
        initServer(self)

        Lists connected elliptec stages, if any, and connects to the first one.
        """
        self.ser = yield self.client.servers[self.serial_server_name]
        yield self.refresh_available_interfaces()

    @inlineCallbacks
    def refresh_available_interfaces(self):
        interfaces = yield self.ser.get_interface_list()
        interfaces = ['ASRL3::INSTR']
        self.interfaces = {}
        for i in interfaces:
            self.ser.select_interface(i)
            self.ser.timeout(50)
            for channel in range(self.N_CHANNELS):
                try:
                    query = '{:x}in'.format(channel)
                    id = yield self.ser.query(query)
                    if len(id) == 33: # Reply is 33 characters
                        self.interfaces["{}:{}".format(i, channel)] = {"device":i, "channel":channel}
                        print("Connected to channel {} on device {}.".format(channel, i))
                    else:
                        raise(IOError("info length was wrong"))
                except Exception as e:
                    print("Could not connect to channel {} on device {}.".format(channel, i))
            self.ser.timeout(3000)

    @inlineCallbacks
    @setting(8, returns='v')
    def get_position(self, c):
        """
        get_position(self, c)
        
        Reads the current position of the selected device

        Args:
            c: The LabRAD context

        Yields:
            float: The stage's position in mm. Note that, if the device is not homed, the value can overflow and be very large.
        """
        self.ser.select_interface(self.interfaces[c['address']]['device'])
        channel = self.interfaces[c['address']]['channel']
        pos = yield self.ser.query("{:x}gp".format(channel))
        returnValue(twos_complement(pos[3:], 32)/self.TICKS_PER_MM)

    @inlineCallbacks
    @setting(9, returns='s')
    def home(self, c):
        """
        home(self, c)

        Move the stage to the home position.

        Args:
            c: The LabRAD context

        Yields:
            str: A serialized JSON describing the stage's status. Includes position if the homing is complete.
        """
        self.ser.select_interface(self.interfaces[c['address']]['device'])
        channel = self.interfaces[c['address']]['channel']
        msg = yield self.ser.query("{:x}ho0".format(channel))
        returnValue(json.dumps(elliptecServer.decode_message(msg)))

    @inlineCallbacks
    @setting(10, returns='s')
    def status(self, c):
        """
        status(self, c)

        Get the status of the stage

        Args:
            c: The LabRAD context

        Yields:
            str: A serialized JSON describing the stage's status.
        """
        self.ser.select_interface(self.interfaces[c['address']]['device'])
        channel = self.interfaces[c['address']]['channel']
        msg = yield self.ser.query("{:x}gs".format(channel))
        returnValue(json.dumps(elliptecServer.decode_message(msg)))

    @inlineCallbacks
    @setting(11, pos='v', returns='s')
    def move_abs(self, c, pos):
        """
        home(self, c)

        Move the stage to the a position relative to home.

        Args:
            c: The LabRAD context
            pos (float): The target position in milimeters

        Yields:
            str: A serialized JSON describing the stage's status. Includes position if the move is complete.
        """
        pos = max(0, min(28, pos))
        self.ser.select_interface(self.interfaces[c['address']]['device'])
        channel = self.interfaces[c['address']]['channel']
        print(pos)
        pos_hex = to_hex(int(pos*self.TICKS_PER_MM), 32)
        print(pos_hex)
        msg = yield self.ser.query("{:x}ma{}".format(channel, pos_hex))
        returnValue(json.dumps(elliptecServer.decode_message(msg)))

    @staticmethod
    def decode_message(msg):
        """
        decode_message(msg)

        Decodes a message from the elliptec stage into a dictionary.

        Args:
            msg (str): A message from the elliptec stage

        Returns:
            dict: A dictionary of the information included in the message
        """
        if msg[1:3] == "PO":
            # Get position
            return {
                'message':msg,
                'status':'OK',
                'position':twos_complement(msg[3:], 32)/elliptecServer.TICKS_PER_MM}
        elif msg[1:3] == "GS":
            try:
                return {
                    'status':elliptecServer.STATUS_DICT[msg[3:5]],
                    'message':msg
                    }
            except Exception as e:
                return {
                'message':msg,
                'status':'confused'}
        else:
            return {'status': 'confused'}

if __name__ == '__main__':
    from labrad import util
    util.runServer(elliptecServer())
