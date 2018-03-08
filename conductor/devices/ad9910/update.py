import sys
sys.path.append('../')
from generic_device.generic_parameter import GenericParameter

from twisted.internet.defer import inlineCallbacks, Deferred
from twisted.internet.reactor import callLater
from labrad.wrappers import connectAsync

from conductor_device.conductor_parameter import ConductorParameter

import serial
import json

arduino_address = 'COM21'


class Update(ConductorParameter):
    priority = 1

    def __init__(self, config={}):
        super(Update, self).__init__(config)
        self.value = self.default

    @inlineCallbacks
    def initialize(self):
        self.cxn = yield connectAsync()
        self.server = self.cxn.polarkrb_ad9910
        interfaces = yield self.server.get_interface_list()
        if len(interfaces) == 1:
            interface = interfaces[0]
        else:
            if arduino_address in interfaces:
               interface = arduino_address
            else:
               interface = interfaces[0]

        yield self.server.select_interface(interface)

    @inlineCallbacks
    def update(self):
        if self.value:
            if self.value == self.default:
                suppress_output = True
            else:
                suppress_output = False

            # Handle a corner case: if the last line in the program is a sweep,
            # the profiles don't work correctly. So ensure that the last line in the program
            # is not a sweep: 
            program = self.value["program"]
            last = program[-1]
            if last["mode"] == "sweep":
                program.append({u"mode": u"single", u"freq": 0, u"ampl": 0, u"phase": 0})

            program = json.dumps(program)
            profiles = json.dumps(self.value["profiles"])
            yield self.server.parse_json_strings_and_update(program, profiles, suppress_output)
        else:
            program = json.dumps(self.default["program"])
            profiles = json.dumps(self.default["profiles"])
            yield self.server.parse_json_strings_and_update(program, profiles, True)

