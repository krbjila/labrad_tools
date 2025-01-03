"""
Provides direct access to serial-enabled hardware.

MAKE SURE YOU CHECK THE WRITE TERMINATION... it is set to ``\r\n`` by default.

..
    ### BEGIN NODE INFO
    [info]
    name = serial
    version = 1
    description =
    instancename = %LABRADNODE%_serial

    [startup]
    cmdline = %PYTHON% %FILE%
    timeout = 20

    [shutdown]
    message = 987654321
    timeout = 20
    ### END NODE INFO
"""
import sys
import pyvisa as visa
from labrad.server import LabradServer, setting
sys.path.append('../')
from server_tools.hardware_interface_server import HardwareInterfaceServer
import json

class SerialServer(HardwareInterfaceServer):
    """Provides direct access to ASRL-enabled hardware."""
    name = '%LABRADNODE%_serial'

    def refresh_available_interfaces(self):
        """ Fill self.interfaces with available connections using Python VISA """
        rm = visa.ResourceManager()
        addresses = rm.list_resources()
        additions = set(addresses) - set(self.interfaces.keys())
        deletions = set(self.interfaces.keys()) - set(addresses)
        for address in additions:
            if address.startswith('ASRL'):
                try:
                    inst = rm.open_resource(address)
                    try:
                        inst.clear()
                    except:
                        pass
                    self.interfaces[address] = inst
                    print('connected to ASRL device ' + address)
                except Exception as e:
                    print("Could not connect to {}: {}".format(address, e))
        for addr in deletions:
            del self.interfaces[addr]

    @setting(3, data='s', returns='')
    def write(self, c, data):
        """
        write(self, c, data)
        
        Write a string to the serial port.

        Args:
            c: The LabRAD context
            data (str): The string to be written to the serial port
        """        
        self.call_if_available('write', c, data)

    @setting(4, n_bytes='w', returns='s')
    def read(self, c, n_bytes=None):
        """
        read(self, c, n_bytes=None)
        
        Read from the serial port.

        Args:
            c: The LabRAD context
            n_bytes (int, optional): If specified, reads only the given number of bytes.
            Otherwise, reads until the device stops sending. Defaults to None.

        Returns:
            str: The bytes returned from the device, with leading and trailing whitespace stripped
        """        
        response = self.call_if_available('read', c)
        return response.strip()

    @setting(8, returns='s')
    def read_line(self, c):
        """
        read_line(self, c)
        
        Reads a line from the serial port (terminated by ``\\n``).

        Args:
            c: The LabRAD context

        Returns:
            str: The bytes returned from the device, with leading and trailing whitespace stripped
        """
        response = self.call_if_available('read', c, '\n') 
        return response.strip()


    @setting(5, data='s', returns='s')
    def query(self, c, data):
        """
        query(self, c, data)
        
        Make a serial query, a write followed by a read.

        This query is atomic.  No other communication to the
        device will occur while the query is in progress.

        Args:
            c: The LabRAD context
            data (str): The string to be written to the serial port

        Returns:
            str: The bytes returned from the device, with leading and trailing whitespace stripped
        """        
#        self.call_if_available('write', c, data)
#        ans = self.call_if_available('read_raw', c)
        response = self.call_if_available('query', c, data)
        return response.strip()

    @setting(6, timeout='v', returns='v')
    def timeout(self, c, timeout=None):
        """
        timeout(self, c, timeout=None)
        
        Sets the timeout associated with the interface

        Args:
            c: The LabRAD context
            timeout (numeric, optional): The timeout for the interface in milliseconds. Defaults to None.

        Returns:
            The timeout in seconds
        """
        interface = self.get_interface(c)
        if timeout is not None:
            interface.timeout = timeout
        return interface.timeout

    @setting(7, write='s', read='s', returns='s')
    def termination(self, c, write=None, read=None):
        """
        termination(self, c, write=None, read=None)

        Sets or gets the read or write terminations.

        TODO: check if you can set terminations for read and write separately (Labrad issue with sending optional args?)

        Args:
            c: The LabRAD context
            write (str, optional): The write termination to set. Defaults to None, in which case the write termination is not set.
            read (str, optional): The read termination to set. Defaults to None, in which case the write termination is not set.

        Returns:
            str: A serialized json containing the write and read terminations.
        """
        interface = self.get_interface(c)
        if write is not None:
            interface.write_termination = write
        if read is not None:
            interface.read_termination = read
        return json.dumps({"read":interface.read_termination, "write":interface.write_termination})

    @setting(9, buffer='s')
    def flush(self, c, buffer=None):
        """
        Flushes the selected device's input or output buffer.

        Args:
            c: The LabRAD context
            buffer (str, optional): "input" or "output" to select the buffer. Defaults to None.
        """
        interface = self.get_interface(c)
        if buffer == 'input':
            interface.flush(visa.constants.VI_READ_BUF)
        elif buffer == 'output':
            interface.flush(visa.constants.VI_WRITE_BUF)

    @setting(10, baud='w', returns='w')
    def baud_rate(self, c, baud=None):
        """
        baud_rate(self, c, baud=None)

        Sets the baud rate of the selected device if baud is not None. Returns the baud rate.

        Args:
            c: The LabRAD context
            baud (int, optional): The baud rate to set. Defaults to None.

        Returns:
            int: The device's current baud rate
        """
        interface = self.get_interface(c)
        if baud is not None:
            interface.baud_rate = baud
        return interface.baud_rate


if __name__ == '__main__':
    from labrad import util
    util.runServer(SerialServer())
