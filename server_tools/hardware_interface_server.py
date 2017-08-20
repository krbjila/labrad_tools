from labrad.server import LabradServer, setting


class HardwareInterfaceServer(LabradServer):
    """ Template for hardware interface server """

    def initServer(self):
        self.interfaces = {}
        self.refresh_available_interfaces()

    def stopServer(self):
        """ notify connected device servers of closing connetion"""

    def refresh_available_interfaces(self):
        """ fill self.interfaces with available hardware """

    def call_if_available(self, f, c, *args, **kwargs):
        try:
            interface = self.get_interface(c)
            ans = getattr(interface, f)(*args, **kwargs)
            return ans
        except:
            try:
                self.refresh_available_interfaces()
                interface = self.get_interface(c)
                return getattr(interface, f)(*args, **kwargs)
            except:
                self.interface = self.get_interface(c)
                return getattr(interface, f)

    def get_interface(self, c):
        if 'address' not in c:
            raise Exception('no interface selected')
        if c['address'] not in self.interfaces.keys():
            self.refresh_available_interfaces()
            if c['address'] not in self.interfaces.keys():
                raise Exception(c['address'] + 'is unavailable')
        return self.interfaces[c['address']]

    @setting(0, returns='*s')
    def get_interface_list(self, c):
        """Get a list of available interfaces"""
        self.refresh_available_interfaces()
        return sorted(self.interfaces.keys())

    @setting(1, address='s', returns='s')
    def select_interface(self, c, address):
        self.refresh_available_interfaces()
        if address not in self.interfaces:
            raise Exception(c['address'] + 'is unavailable')
        c['address'] = address
        return c['address'] 
