import os, sys
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..'))

from server_tools.device_server import DeviceServer, DeviceWrapper, get_connection_wrapper, get_device_wrapper
from twisted.internet.defer import inlineCallbacks, returnValue
from labrad.server import setting

import traceback 

class PicomotorServer(DeviceServer):
    name = '%LABRADNODE%_picomotor'

    def _select_device(self, c):
        try:
            name = c['name']
        except KeyError:
            raise Exception('Please select a device first; devices: {}'.format(self.devices.keys()))
        dev = self.devices[name]
        return dev
    
    @inlineCallbacks
    def call_if_available(self, c, method, *args):
        try:
            result = yield method(*args)
            returnValue(result)
        except Exception as e:
            print("Error calling {} with args {}:".format(method, args))
            print("Reinitializing connection and trying again...")
            try:
                yield self.reinit_connection(c)
                result = yield method(*args)
                returnValue(result)
            except Exception as e:
                print("Error calling {} with args {}:".format(method, args))
                print(e)
    
    @inlineCallbacks
    @setting(10, 'get position', axis='i', returns='i')
    def get_position(self, c, axis):
        dev = self._select_device(c)
        position = yield self.call_if_available(c, dev.get_position, axis)
        returnValue(position)

    @inlineCallbacks
    @setting(11, 'move rel', axis='i', distance='i')
    def move_rel(self, c, axis, distance):
        dev = self._select_device(c)
        yield self.call_if_available(c, dev.move_rel, axis, distance)

    @inlineCallbacks
    @setting(12, 'abort')
    def abort(self, c):
        dev = self._select_device(c)
        yield self.call_if_available(c, dev.abort)

    @inlineCallbacks
    @setting(13, 'stop', axis='i')
    def stop(self, c, axis):
        dev = self._select_device(c)
        yield self.call_if_available(c, dev.stop, axis)

    @inlineCallbacks
    @setting(14, 'set home', axis='i', position='i')
    def set_home(self, c, axis, position=0):
        dev = self._select_device(c)
        yield self.call_if_available(c, dev.set_home, axis, position)

    @inlineCallbacks
    @setting(15, 'motor check')
    def motor_check(self, c):
        dev = self._select_device(c)
        yield self.call_if_available(c, dev.motor_check)

    @inlineCallbacks
    @setting(16, 'save settings')
    def save_settings(self, c):
        dev = self._select_device(c)
        yield self.call_if_available(c, dev.save_settings)

    @inlineCallbacks
    @setting(17, 'query motor type', axis='i', returns='i')
    def query_motor_type(self, c, axis):
        dev = self._select_device(c)
        type = yield self.call_if_available(c, dev.query_motor_type, axis)
        returnValue(type)

    @inlineCallbacks
    @setting(18, 'move abs', axis='i', position='i')
    def move_abs(self, c, axis, position):
        dev = self._select_device(c)
        yield self.call_if_available(c, dev.move_abs, axis, position)

    @inlineCallbacks
    @setting(19, 'motion done', axis='i', returns='b')
    def motion_done(self, c, axis):
        dev = self._select_device(c)
        done = yield self.call_if_available(c, dev.motion_done, axis)
        returnValue(done)

    @inlineCallbacks
    @setting(20, 'set velocity', axis='i', speed='i')
    def set_velocity(self, c, axis, speed):
        dev = self._select_device(c)
        yield self.call_if_available(c, dev.set_velocity, axis, speed)

    @inlineCallbacks
    @setting(21, 'get velocity', axis='i', returns='i')
    def get_velocity(self, c, axis):
        dev = self._select_device(c)
        speed = yield self.call_if_available(c, dev.get_velocity, axis)
        returnValue(speed)

    @inlineCallbacks
    @setting(22, 'reset')
    def reset(self, c):
        dev = self._select_device(c)
        yield self.call_if_available(c, dev.reset)

if __name__ == '__main__':
    from labrad import util
    util.runServer(PicomotorServer("picomotor_config.json"))

