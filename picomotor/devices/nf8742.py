from server_tools.device_server import DeviceWrapper
from twisted.internet.defer import inlineCallbacks, returnValue

BUFFER_SIZE = 1024

class NF8742(DeviceWrapper):
    @inlineCallbacks
    def set_position(self, position):
        command = '{}PA{}\n'.format(self.axis, position)
        yield self.connection.send(command)

    @inlineCallbacks
    def get_position(self):
        command = '{}PA?\n'.format(self.axis)
        yield self.connection.send(command)
        ans = yield self.connection.recv(BUFFER_SIZE)
        returnValue(int(ans))

