"""
Provides access to Rigol DG800 series AWGs.

..
    ### BEGIN NODE INFO
    [info]
    name = dg800
    version = 1
    description = server for Rigol DG800 series AWGs
    instancename = %LABRADNODE%_dg800

    [startup]
    cmdline = %PYTHON% %FILE%
    timeout = 20

    [shutdown]
    message = 987654321
    timeout = 20
    ### END NODE INFO
"""
import sys
from labrad.util import getNodeName
from labrad.server import LabradServer, setting
from twisted.internet.defer import inlineCallbacks, returnValue

class DG800Server(LabradServer):
    """Provides access to Rigol DG800 series AWGs."""
    name = '%LABRADNODE%_dg800'

    def __init__(self):
        LabradServer.__init__(self)
    
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

    @setting(7, channel='i', freq='v', amplitude='v', offset='v', phase='v')
    def set_sin(self, c, channel, freq, amplitude, offset, phase):
        """
        set_sin(self, c, channel, freq, amplitude, offset, phase)
        
        Get the settings for a channel with sine output

        Args:
            c: A LabRAD context (not used)
            channel (int): Which channel to get settings for. Must be 1 or 2
            freq (float): The frequency in Hertz (1E-6 to 35E6)
            amplitude (float): The amplitude in Volts (limited by impedance and amplitude high level settings)
            offset (float): The offset in Volts (limited by impedance and amplitude high level settings)
            phase (float): The phase in degrees (0 to 360)

        """
        if channel not in [1,2]:
            raise ValueError("Channel {} invalid. Acceptable values are 1 or 2.".format(channel))
        yield self.USB.write(":SOUR%d:APPL:SIN %f,%f,%f,%f" % (channel, min(35E6,max(1E-6,freq)), amplitude, offset, phase))

    @setting(8, channel='i', enable='b')
    def set_output(self, c, channel, enable):
        """
        set_output(self, c, channel, enable)
        
        Enables or disables one of the AWG's outputs

        Args:
            c: A LabRAD context (not used)
            channel (int): Which channel to set the output enable status. Must be 1 or 2
            enable (bool): True if the channel is enabled, False otherwise
        """
        if channel not in [1,2]:
            raise ValueError("Channel {} invalid. Acceptable values are 1 or 2.".format(channel))
        if enable:
            stringthing = 'ON'
        else:
            stringthing = 'OFF'
        yield self.USB.write(":OUTP%d %s" % (channel, stringthing))

    @setting(11, channel='i', impedance='i', inf='b', low='b')
    def set_impedance(self, c, channel, impedance=50, inf=False, low=False):
        """
        set_impedance(self, c, channel, impedance=50, inf=False, low=False)
        
        Set the output impedance of a channel either to 

        Args:
            c: A LabRAD context (not used)
            channel (int): Which channel to set the output impedance for. Must be 1 or 2
            impedance (numeric, optional): Output impedance in Ohms. Defaults to 50, is coerced to be between 1 and 10000.
            inf (bool, optional): Sets the output to high imedance. Takes precedence over the impedance option and low impedance mode. Defaults to False.
            low (bool, optional): Sets the output to minimum impedance. Takes precedence over the impedance option. Defaults to False.
        """

        if channel not in [1,2]:
            raise ValueError("Channel {} invalid. Acceptable values are 1 or 2.".format(channel))
        if inf:
            yield self.USB.write(":OUTP%d:IMP INF" % (channel))

        elif low:
            yield self.USB.write(":OUTP%d:IMP MIN" % (channel))

        else:
            yield self.USB.write(":OUTP%d:IMP %d" % (channel, min(10000,max(1,impedance))))

    @setting(12, channel='i', ncycles='i')
    def set_ncycles(self, c, channel, ncycles):
        """
        set_ncycles(self, c, channel, ncycles)
        
        Sets the number of cycles to run per trigger, if the mode is set to triggered by :meth:`set_gated`.

        Args:
            c: A LabRAD context (not used)
            channel (int): Which channel to set the number of cycles for. Must be 1 or 2
            ncycles (int): The number of cycles to run per trigger. Coerced to between 1 and 500000
        """
        if channel not in [1,2]:
            raise ValueError("Channel {} invalid. Acceptable values are 1 or 2.".format(channel))
        yield self.USB.write(":SOUR%d:BURS:NCYC %d" % (channel, min(500000,max(1,ncycles))))

    @setting(13, channel='i', gated='b')
    def set_gated(self, c, channel, gated):
        """
        set_gated(self, c, channel, gated)
        
        Sets a channel to either be gated or triggered by the external output

        Args:
            c: A LabRAD context (not used)
            channel (int): Which channel to set the gating mode for. Must be 1 or 2
            gated (bool): Whether the channel is gated (True) or triggered (False)
        """
        if channel not in [1,2]:
            raise ValueError("Channel {} invalid. Acceptable values are 1 or 2.".format(channel))
        if gated:
            yield self.USB.write(":SOUR%d:BURS:MODE GAT" % (channel))
        else:
            yield self.USB.write(":SOUR%d:BURS:MODE TRIG" % (channel))

    @setting(9, channel='i', returns='*v')
    def get_sin(self, c, channel):
        """
        get_sin(self, c, channel)
        
        Get the settings for a channel with sine output

        Args:
            c: A LabRAD context (not used)
            channel (int): Which channel to get settings for. Must be 1 or 2

        Returns:
            A list of floats: The frequency (Hz), amplitude (V), offset (V) and phase (deg) of the channel's sine wave. If the channel is not in sine mode, returns :code:`[0]`.
        """
        if channel not in [1,2]:
            raise ValueError("Channel {} invalid. Acceptable values are 1 or 2.".format(channel))
        out = yield self.USB.query(":SOUR%d:APPL?" % (channel))
        splits = out.replace('"','').split(',')
        if 'SIN' in splits[0]:
            returnValue([float(i) for i in splits[1:]])
        else:
            returnValue([0])

    @setting(10, channel='i', returns='b')
    def get_output(self, c, channel):
        """
        get_output(self, c, channel)
        
        Check whether an output is enabled

        Args:
            c: A LabRAD context (not used)
            channel (int): Which channel to get output status. Must be 1 or 2

        Returns:
            boolean: whether the channel's output is enabled
        """
        if channel not in [1,2]:
            raise ValueError("Channel {} invalid. Acceptable values are 1 or 2.".format(channel))
        stringthing = yield self.USB.query(":OUTP%d?" % (channel))
        out = 'ON' in stringthing
        returnValue(out)

if __name__ == '__main__':
    from labrad import util
    util.runServer(DG800Server())
