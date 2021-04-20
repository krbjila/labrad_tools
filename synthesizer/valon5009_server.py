"""
Provides access to Valon 5009 synthesizer

..
    ### BEGIN NODE INFO
    [info]
    name = valon5009
    version = 1
    description = server for Valon 5009 synthesizer
    instancename = %LABRADNODE%_valon5009

    [startup]
    cmdline = %PYTHON% %FILE%
    timeout = 20

    [shutdown]
    message = 987654321
    timeout = 20
    ### END NODE INFO
"""

import sys, re
from labrad.server import LabradServer, setting
from labrad.util import getNodeName
from twisted.internet.defer import inlineCallbacks, returnValue

baud_rates = [115200, 9600]

class Valon5009Server(LabradServer):
    """Provides access to Valon 5009 synthesizer"""
    name = '%LABRADNODE%_valon5009'

    def __init__(self):
        LabradServer.__init__(self)
    
    @inlineCallbacks
    def initServer(self):
        self.USB_server_name = '{}_usb'.format(getNodeName())
        self.USB = yield self.client.servers[self.USB_server_name]

    @inlineCallbacks
    @setting(5, returns='*s')
    def get_devices(self, c):
        """
        get_devices(self, c)

        Lists the Valon devices connected via USB.

        The logic is a little convoluted since the Valon doesn't respond to the standard '*IDN' command and echos the commands it receives.

        Args:
            c: The LabRAD conext

        Yields:
            A list of strings: The PyVISA ID strings for the connected Valon devices
        """
        interfaces = yield self.USB.get_interface_list()
        self.devices = []
        for i in interfaces:
            self.select_device(c, i)
            print("selecting {}".format(i))
            old_baud_rate = yield self.USB.baud_rate()
            for baud_rate in baud_rates:
                try:
                    print("Setting baud rate to " + str(baud_rate))
                    yield self.USB.baud_rate(baud_rate)
                    yield self.USB.clear()
                    print("querying *IDN?")
                    id1 = yield self.USB.query('*IDN?')
                    if '*IDN?' in id1:
                        id1 = yield self.USB.read()
                    if "Illegal command!" in id1:
                        # next_line = yield self.USB.read()
                        # next_next_line = yield self.USB.read()
                        # if 'IDN*' in next_line and "Command error!" in next_next_line:
                        yield self.USB.clear()
                        yield self.USB.query('ID')
                        id2 = yield self.USB.read()
                        if "Valon" in id2:
                            self.devices.append(i)
                            break
                except Exception as e:
                    print("Setting baud rate to " + str(old_baud_rate))
                    yield  self.USB.baud_rate(old_baud_rate)
                    if "exceptions.AttributeError" in e.msg:
                        pass
                    else:
                        raise Exception(e.msg)
        print("Connected to {}".format(self.devices))
        returnValue(self.devices)

    @setting(6, device='s')
    def select_device(self, c, device):
        """
        select_device(self, c, device)
        
        Selects a connected device.

        Args:
            c: The LabRAD context (not used)
            device (string): PyVISA ID, as returned by :meth:`valon5009_server.get_devices`
        """
        self.USB.select_interface(device)

    @setting(7, channel='i')
    def set_channel(self, c, channel):
        """
        set_channel(self, c, channel)
        
        Selects whether channel 1 or 2 is to be controlled.

        Args:
            c: The LabRAD context (not used)
            channel (int): 1 or 2
        """
        if not channel in [1, 2]:
            print("Valon5009 set_channel error: channel must be 1 or 2")
        else:
            self.USB.clear()
            yield self.USB.query("SOUR {}".format(channel))

    @inlineCallbacks
    @setting(8, attenuation='v', returns='v')
    def set_attenuation(self, c, attenuation):
        """set_attenuation(self, c, attenuation)
        
        Sets the attenuation of the currently selected channel.

        Args:
            c: The LabRAD context (not used)
            power (numeric): The attenuation in dB. Coerced to between 0 and 31.5, rounded to the nearest 0.5.

        Returns:
            float: The value that the attenuator is set to. May be different than the commanded value because of rounding.
        """
        attenuation = max(min(31.5, attenuation), 0)
        self.USB.clear()
        yield self.USB.query("ATT {}".format(attenuation))
        reply = yield self.USB.read()
        returnValue(float(re.findall(r'\d*\.?\d+', reply)[0]))

    @setting(9, enable='b')
    def set_enable(self, c, enable):
        """
        set_enable(self, c, enable)
        
        Selects whether the selected channel's output buffer amplifier is enabled. Disabling the output does not completely disable the output, but reduces its power by approximately 50 dB.

        Args:
            c: The LabRAD context (not used)
            enable (boolean): False for disabled, True for enabled
        """
        self.USB.clear()
        yield self.USB.query("OEN {}".format("1" if enable else "0"))
        yield self.USB.read()

    @setting(10, mode='s')
    def set_mode(self, c, mode):
        """set_mode(self, c, mode)
        
        Sets the mode of the synthesizer.

        Args:
            c: The LabRAD context (not used)
            mode (string): Must be one of "CW", "SWE", or "LIST"
        """
        self.USB.clear()
        if mode in ["CW", "SWE", "LIST"]:
            yield self.USB.query("MODE {}".format(mode))
            yield self.USB.read()
        else:
            raise ValueError("Mode {} not one of 'CW', 'SWE', or 'LIST'.".format(mode))
    
    @inlineCallbacks
    @setting(11, freq='v', returns='v')
    def set_freq(self, c, freq):
        """
        set_freq(self, c, freq)
        
        Sets the CW frequency of the currently selected channel.

        Args:
            c: The LabRAD context (not used)
            freq (numeric): The frequency in MHz. Coerced to between 23.5 and 6000.

        Yields:
            float: The value that the frequency is set to, in MHz. May be different than the commanded value because of rounding.
        """
        freq = max(min(6000, freq), 23.5)
        self.USB.clear()
        yield self.USB.query("F {}m".format(freq))
        reply = yield self.USB.read()
        returnValue(float(re.findall(r'\d*\.?\d+', reply)[1]))

    @setting(12, mode='s')
    def set_trig(self, c, mode):
        """
        set_trig(self, c, mode)
        
        Sets the sweep trigger mode of the synthesizer.

        Args:
            c: The LabRAD context (not used)
            mode (string): Must be one of "AUTO", "MAN", or "EXT"
        """
        if mode in ["AUTO", "MAN", "EXT"]:
            self.USB.clear()
            yield self.USB.query("MODE {}".format(mode))
            yield self.USB.read()
        else:
            raise ValueError("Mode {} not one of 'AUTO', 'MAN', or 'EXT'.".format(mode))
    
    @setting(13)
    def trig(self, c):
        """
        trig(self, c)
        
        Triggers a sweep, if the trigger mode is set to "MAN" and the mode is set to "SWE"

        Args:
            c: The LabRAD context (not used)
        """
        self.USB.clear()
        yield self.USB.query("TRGR")

    @setting(14)
    def save(self, c):
        """
        save(self, c)
        
        Saves the current settings to flash memory. The synthesizer will load the saved state when next turned on.

        Args:
            c: The LabRAD context (not used)
        """
        self.USB.clear()
        yield self.USB.query("SAVE")

    @setting(15)
    def reset(self, c):
        """
        reset(self, c)
        
        Resets the synthesizer to factory default settings.

        Args:
            c: The LabRAD context (not used)
        """
        self.USB.clear()
        yield self.USB.query("RST")
    
    @inlineCallbacks
    @setting(16, returns='v')
    def get_freq(self, c):
        """
        get_freq(self, c)
        
        Gets the frequency of the current source.

        Args:
            c: The LabRAD context (not used)

        Returns:
            float: The frequency of the current source in MHz
        """
        self.USB.clear()
        yield self.USB.query("FREQ?")
        reply = yield self.USB.read()
        returnValue(float(re.findall(r'\d*\.?\d+', reply)[1]))

    @inlineCallbacks
    @setting(17, rate='v', returns='v')
    def set_rate(self, c, rate):
        """
        set_rate(self, c, rate)
        
        Sets the sweep step rate for the selected channel.

        Args:
            c: The LabRAD context (not used)
            rate (numeric): The step rate in ms. Coerced to between 0.1 and 715827.882.

        Yields:
            float: The value that the rate is set to, in ms. May be different than the commanded value because of rounding.
        """
        rate = max(min(715827.882, rate), 0.1)
        self.USB.clear()
        yield self.USB.query("RATE {}m".format(rate))
        reply = yield self.USB.read()
        returnValue(float(re.findall(r'\d*\.?\d+', reply)[0]))

    @inlineCallbacks
    @setting(18, freq='v', returns='v')
    def set_start(self, c, freq):
        """
        set_start(self, c, freq)
        
        Sets the sweep start frequency of the currently selected channel.

        Args:
            c: The LabRAD context (not used)
            freq (numeric): The frequency in MHz. Coerced to between 23.5 and 6000.

        Yields:
            float: The value that the start frequency is set to, in MHz. May be different than the commanded value because of rounding.
        """
        freq = max(min(6000, freq), 23.5)
        self.USB.clear()
        yield self.USB.query("START {}m".format(freq))
        reply = yield self.USB.read()
        returnValue(float(re.findall(r'\d*\.?\d+', reply)[1]))

    @inlineCallbacks
    @setting(19, freq='v', returns='v')
    def set_stop(self, c, freq):
        """
        set_stop(self, c, freq)
        
        Sets the sweep end frequency of the currently selected channel.

        Args:
            c: The LabRAD context (not used)
            freq (numeric): The frequency in MHz. Coerced to between 23.5 and 6000.

        Yields:
            float: The value that the end frequency is set to, in MHz. May be different than the commanded value because of rounding.
        """
        freq = max(min(6000, freq), 23.5)
        self.USB.clear()
        yield self.USB.query("STOP {}m".format(freq))
        reply = yield self.USB.read()
        returnValue(float(re.findall(r'\d*\.?\d+', reply)[1]))

    @inlineCallbacks
    @setting(20, time='v', returns='v')
    def set_rtime(self, c, time):
        """
        set_rtime(self, c, time)
        
        Sets the dwell interval before the start of a new sweep for the selected channel.

        Args:
            c: The LabRAD context (not used)
            time (numeric): The dwell time in ms. Coerced to between 0.1 and 715827.882.

        Yields:
            float: The value that the dwell time is set to, in ms. May be different than the commanded value because of rounding.
        """
        freq = max(min(715827.882, time), 0.1)
        self.USB.clear()
        yield self.USB.query("RTIME {}m".format(time))
        reply = yield self.USB.read()
        returnValue(float(re.findall(r'\d*\.?\d+', reply)[0]))
    
    @inlineCallbacks
    @setting(21, returns='b')
    def run(self, c):
        """
        run(self, c)
        
        Starts the sweep if the instrument is in SWEEP mode with trigger mode AUTO.

        Args:
            c: The LabRAD context (not used)

        Returns:
            boolean: True if the sweep was run, False otherwise
        """

        self.USB.clear()
        yield self.USB.query("MODE")
        reply1 = yield self.USB.read()
        if "SWEEP" in reply1:
            yield self.USB.query("TMODE")
            reply2 = yield self.USB.read()
            if "AUTO" in reply2:
                yield self.USB.query("RUN")
                returnValue(True)
        returnValue(False)

    @inlineCallbacks
    @setting(22, returns='b')
    def halt(self, c):
        """
        halt(self, c)
        
        Stops the sweep if the instrument is in SWEEP mode with trigger mode AUTO.

        Args:
            c: The LabRAD context (not used)

        Returns:
            boolean: True if the sweep was stopped, False otherwise
        """

        self.USB.clear()
        yield self.USB.query("MODE")
        reply1 = yield self.USB.read()
        if "SWEEP" in reply1:
            yield self.USB.query("TMODE")
            reply2 = yield self.USB.read()
            if "AUTO" in reply2:
                yield self.USB.query("HALT")
                returnValue(True)
        returnValue(False)


if __name__ == '__main__':
    from labrad import util
    util.runServer(Valon5009Server())
