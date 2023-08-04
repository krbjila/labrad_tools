import socket

from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.internet.threads import deferToThread

class SocketConnection(object):
    @inlineCallbacks
    def initialize(self, device):
        self.connection = socket.create_connection(
                (device.servername, int(device.address)), timeout=5)
        try:
            yield self.recv(1024)
        except socket.timeout:
            pass

    @inlineCallbacks 
    def send(self, value):
        nbytes = yield deferToThread(self.connection.send, value)
        # nbytes = yield self.connection.send(value)
        returnValue(nbytes)
    
    @inlineCallbacks 
    def recv(self, value):
        response = yield deferToThread(self.connection.recv, value)
        # response = yield self.connection.recv(value)
        returnValue(response)

    @inlineCallbacks
    def query(self, value):
        yield self.send(value)
        response = yield self.recv(1024)
        returnValue(response)
    
    def getsockname(self):
        return self.connection.getsockname()
