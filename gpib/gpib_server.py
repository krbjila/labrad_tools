"""
Provides direct access to USB-enabled hardware.

..
    ### BEGIN NODE INFO
    [info]
    name = gpib
    version = 1
    description =
    instancename = %LABRADNODE%_gpib

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

from pathlib import Path
sys.path.append([str(i) for i in Path(__file__).parents if str(i).endswith("labrad_tools")][0])
from server_tools.hardware_interface_server import HardwareInterfaceServer
class GPIBServer(HardwareInterfaceServer):
    """Provides direct access to GPIB-enabled hardware."""
    name = '%LABRADNODE%_gpib'

    def refresh_available_interfaces(self):
        """ Fill self.interfaces with available connections using Python VISA """
        rm = visa.ResourceManager('@py')
        addresses = rm.list_resources()
        additions = set(addresses) - set(self.interfaces.keys())
        deletions = set(self.interfaces.keys()) - set(addresses)
        for address in additions:
            if address.startswith('GPIB'):
                inst = rm.open_resource(address)
                inst.write_termination = ''
                #inst.clear()
                self.interfaces[address] = inst
                print('connected to GPIB device {}'.format(address)) 
        for addr in deletions:
            del self.interfaces[addr]

    @setting(3, data='s', returns='')
    def write(self, c, data):
        """
        write(self, c, data)
        
        Write a string to the GPIB bus.

        Args:
            c: The LabRAD context
            data (string): The string to be written to the GPIB bus
        """   
        self.call_if_available('write', c, data)

    @setting(4, n_bytes='w', returns='s')
    def read(self, c, n_bytes=None):
        """
        read(self, c, n_bytes=None)
        
        Read from the GPIB bus.

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
        
        Make a GPIB query, a write followed by a read.

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


if __name__ == '__main__':
    from labrad import util
    util.runServer(GPIBServer())
