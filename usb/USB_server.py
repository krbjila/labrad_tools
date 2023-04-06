"""
Provides direct access to USB-enabled hardware.

..
    ### BEGIN NODE INFO
    [info]
    name = usb
    version = 1
    description =
    instancename = %LABRADNODE%_usb

    [startup]
    cmdline = %PYTHON% %FILE%
    timeout = 20

    [shutdown]
    message = 987654321
    timeout = 20
    ### END NODE INFO
"""
import sys
import pyvisa
from labrad.server import LabradServer, setting
sys.path.append('../')
from server_tools.hardware_interface_server import HardwareInterfaceServer


class USBServer(HardwareInterfaceServer):
    """Provides direct access to USB-enabled hardware."""
    name = '%LABRADNODE%_usb'

    def refresh_available_interfaces(self):
        """ Fill self.interfaces with available connections using Python VISA """
        rm = pyvisa.ResourceManager()
        addresses = rm.list_resources()
        additions = set(addresses) - set(self.interfaces.keys())
        deletions = set(self.interfaces.keys()) - set(addresses)
        for address in additions:
            if address.startswith('USB'):
                inst = rm.open_resource(address)
                inst.write_termination = ''
                #inst.clear()
                self.interfaces[address] = inst
                print('connected to USB device ' + address)
        for addr in deletions:
            del self.interfaces[addr]

    @setting(3, data='s', returns='')
    def write(self, c, data):
        """
        write(self, c, data)
        
        Write a string to the USB bus.

        Args:
            c: The LabRAD context
            data (string): The string to be written to the USB bus
        """        
        self.call_if_available('write', c, data)

    @setting(4, n_bytes='w', returns='s')
    def read(self, c, n_bytes=None):
        """
        read(self, c, n_bytes=None)
        
        Read from the USB bus.

        Args:
            c: The LabRAD context
            n_bytes (int, optional): If specified, reads only the given number of bytes.
            Otherwise, reads until the device stops sending. Defaults to None.

        Returns:
            string: The bytes returned from the device, with leading and trailing whitespace stripped
        """        
        response = self.call_if_available('read', c)
        return response.strip()

    @setting(5, data='s', returns='s')
    def query(self, c, data):
        """
        query(self, c, data)
        
        Make a USB query, a write followed by a read.

        This query is atomic.  No other communication to the
        device will occur while the query is in progress.

        Args:
            c: The LabRAD context
            data (string): The string to be written to the USB bus
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
            timeout (numeric, optional): The timeout for the interface in seconds. Defaults to None.

        Returns:
            The timeout in milliseconds
        """
        interface = self.get_interface(c)
        if timeout is not None:
            interface.timeout = timeout
        return interface.timeout

    @setting(7, write='s', read='s', returns='(s,s)')
    def termination(self, c, write=None, read=None):
        """
        termination(self, c, write=None, read=None)

        Sets or gets the read or write terminations.

        Args:
            c: The LabRAD context
            write (str, optional): The write termination to set. Defaults to None, in which case the write termination is not set.
            read (str, optional): The read termination to set. Defaults to None, in which case the write termination is not set.

        Returns:
            (str, str): A tuple containing the write and read terminations.
        """
        interface = self.get_interface(c)
        if write is not None:
            interface.write_termination = write
        if read is not None:
            interface.read_termination = read
        return (interface.write_termination, interface.read_termination)

    @setting(8, baud_rate='i', returns='i')
    def baud_rate(self, c, baud_rate=None):
        """
        baudrate(self, c, baud_rate=None)

        Sets or gets the baudrate

        Args:
            c: The LabRAD context
            baud_rate (int, optional): The baud rate to set. Defaults to None, in which case the baud rate is not set.

        Returns:
            (int): The current baud rate
        """
        interface = self.get_interface(c)
        if baud_rate  is not None:
            interface.baud_rate  = baud_rate 
        return interface.baud_rate 

if __name__ == '__main__':
    from labrad import util
    util.runServer(USBServer())
