from __future__ import print_function
import sys
sys.path.append('../')
from generic_device.generic_parameter import GenericParameter

from twisted.internet.defer import inlineCallbacks, Deferred
from twisted.internet.reactor import callLater
from labrad.wrappers import connectAsync

from conductor_device.conductor_parameter import ConductorParameter

import json

CHANNEL_NAME = "Up Leg Double Pass"
DEVICE = '3xAD9959_0'

class Uplegdp(ConductorParameter):
    priority = 1

    def __init__(self, config={}):
        super(Uplegdp, self).__init__(config)
        try:
            self.value = self.default
        except AttributeError:
            # a default was never loaded
            # this can happen if the parameter was called
            # with invalid arguments.
            self.value = 0
            self.default = 0

    @inlineCallbacks
    def initialize(self):
        self.cxn = yield connectAsync()
        yield self.getChannelInfo()

    @inlineCallbacks
    def getChannelInfo(self):
        try:
            # Try to connect to the DDS server
            self.server = self.cxn.krbg2_dds

            s = yield self.server.get_channels()

            # Verify that your channel name is okay
            channels = json.loads(s)
            try:
                c = channels[CHANNEL_NAME]
                self.address = c['loc']
                self.alive = True
            # If not, give error message
            except KeyError:
                print("Couldn't find channel \"{}\".".format(CHANNEL_NAME))
                print("Available channels:")
                for key in channels.keys():
                    print(key)
            except Exception as e:
                print(e)
        except AttributeError:
            # Log a warning that the server can't be found.
            # Conductor will throw an error and remove the parameter
            print("3xAD9959_0's uplegdp: KRbG2 server not connected.")

    @inlineCallbacks
    def update(self):
        # Sketchy way of checking for self.address attribute error
        try:
            if self.address:
                pass
        except AttributeError:
            try:
                yield self.getChannelInfo()
            except:
                print("3xAD9959_0's uplegdp: Tried to get address but failed :(")

        try:
            if self.value:
                d = {
                    DEVICE : [
                        {
                            'address': self.address,
                            'frequency': self.value
                        }
                    ]
                }
                yield self.server.update_dds(json.dumps(d))
        except Exception as e:
            print(e)
            print("3xAD9959_0's uplegdp: didn't update")
