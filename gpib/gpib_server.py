"""
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
from __future__ import print_function
import sys

import visa

from labrad.server import LabradServer, setting

sys.path.append('../')
from server_tools.hardware_interface_server import HardwareInterfaceServer


class GPIBServer(HardwareInterfaceServer):
    """Provides direct access to GPIB-enabled hardware."""
    name = '%LABRADNODE%_gpib'

    def refresh_available_interfaces(self):
        """ fill self.interfaces with available connections """
        """ Modified to use python visa """
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
                print('connected to GPIB device ' + address)
        for addr in deletions:
            del self.interfaces[addr]

    @setting(3, data='s', returns='')
    def write(self, c, data):
        """Write a string to the GPIB bus."""
        self.call_if_available('write', c, data)

    @setting(4, n_bytes='w', returns='s')
    def read(self, c, n_bytes=None):
        """Read from the GPIB bus.

        If specified, reads only the given number of bytes.
        Otherwise, reads until the device stops sending.
        """
        response = self.call_if_available('read', c)
        return response.strip()

    @setting(5, data='s', returns='s')
    def query(self, c, data):
        """Make a GPIB query, a write followed by a read.

        This query is atomic.  No other communication to the
        device will occur while the query is in progress.
        """
#        self.call_if_available('write', c, data)
#        ans = self.call_if_available('read_raw', c)
        response = self.call_if_available('query', c, data)
        return response.strip()

    @setting(6, timeout='v', returns='v')
    def timeout(self, c, timeout=None):
        interface = self.get_interface(c)
        if timeout is not None:
            interface.timeout = timeout
        return interface.timeout


if __name__ == '__main__':
    from labrad import util
    util.runServer(GPIBServer())
