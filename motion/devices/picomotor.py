import os, sys
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), '../..'))

from server_tools.device_server import DeviceWrapper
from twisted.internet.defer import inlineCallbacks, returnValue

def validate_axis(axis):
    if int(axis) not in [1,2,3,4]:
        raise Exception('Axis must be 1, 2, 3, or 4')
    return int(axis)

def validate_distance(distance):
    distance = int(distance)
    if distance <-2147483648 or distance > 2147483647:
        raise Exception('Distance must be between -2147483648 and 2147483647')
    return distance

def validate_speed(speed):
    speed = int(speed)
    if speed < 0 or speed > 2000:
        raise Exception('Speed must be between 0 and 2000 steps per second')
    return speed

class Picomotor(DeviceWrapper):

    def __init__(self, config):
        super().__init__(config)

    def send(self, command):
        self.connection.send((command+'\r'))

    def query(self, command):
        return self.connection.query(command+'\r')

    @inlineCallbacks
    def get_position(self, axis):
        axis = validate_axis(axis)
        position = yield self.query('{}TP?'.format(axis))
        returnValue(int(position))

    @inlineCallbacks
    def move_rel(self, axis, distance):
        axis = validate_axis(axis)
        distance = validate_distance(distance)
        yield self.send('{}PR{}'.format(axis, distance))

    @inlineCallbacks
    def abort(self):
        yield self.send('AB')

    @inlineCallbacks
    def stop(self, axis):
        axis = validate_axis(axis)
        yield self.send('{}ST'.format(axis))

    @inlineCallbacks
    def set_home(self, axis, position=0):
        axis = validate_axis(axis)
        position = validate_distance(position)
        yield self.send('{}DH{}'.format(axis, position))

    @inlineCallbacks
    def motor_check(self):
        yield self.send('MC')

    @inlineCallbacks
    def save_settings(self):
        yield self.send('SM')

    @inlineCallbacks
    def move_abs(self, axis, position):
        axis = validate_axis(axis)
        position = validate_distance(position)
        yield self.send('{}PA{}'.format(axis, position))

    @inlineCallbacks
    def motion_done(self, axis):
        axis = validate_axis(axis)
        done = yield self.query('{}MD?'.format(axis))
        returnValue(bool(done))

    @inlineCallbacks
    def query_motor_type(self, axis):
        axis = validate_axis(axis)
        type = yield self.query('{}QM?'.format(axis))
        returnValue(int(type))

    @inlineCallbacks
    def set_velocity(self, axis, speed):
        axis = validate_axis(axis)
        speed = validate_speed(speed)
        yield self.send('{}VA{}'.format(axis, speed))

    @inlineCallbacks
    def get_velocity(self, axis):
        axis = validate_axis(axis)
        speed = yield self.query('{}VA?'.format(axis))
        returnValue(int(speed))

    @inlineCallbacks
    def reset(self):
        yield self.send('*RST')