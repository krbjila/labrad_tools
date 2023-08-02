import clr, sys
from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.internet.threads import deferToThread

clr.AddReference("C:\\Program Files\\Newport\\Newport USB Driver\\Bin\\UsbDllWrap")

from Newport.USBComm import *
from System.Text import StringBuilder
from System.Collections import Hashtable
from System.Collections import IDictionaryEnumerator

class NewportConnection(object):
    @inlineCallbacks
    def initialize(self, device):
        self.oUSB = USB(True)
        bStatus = yield self.oUSB.OpenDevices(0, True)
        oDeviceTable = yield self.oUSB.GetDeviceTable()
        nDeviceCount = oDeviceTable.Count
        
        if nDeviceCount == 0:
            raise Exception('No discovered devices')
        
        oEnumerator = oDeviceTable.GetEnumerator()
        strDeviceKeyList = []

        for nIdx in range(0, nDeviceCount):
            if oEnumerator.MoveNext():
                if str(oEnumerator.Key) == device.address:
                    self.connection = str(oEnumerator.Key)
                    break
        if self.connection is None:
            raise Exception('Device {} not found'.format(device.address))
        print('Connected to {}'.format(self.connection))

    @inlineCallbacks 
    def query(self, value):
        strBldr = StringBuilder(64)
        strBldr.Remove(0, strBldr.Length)
        nReturn = yield self.oUSB.Query(self.connection, value, strBldr)
        if nReturn != 0:
            raise Exception('Query returned {}'.format(nReturn))
        returnValue(strBldr.ToString())

    @inlineCallbacks
    def send(self, value):
        nReturn = yield self.oUSB.Write(self.connection, value)
        if nReturn != 0:
            raise Exception('Send returned {}'.format(nReturn))
        returnValue(nReturn)