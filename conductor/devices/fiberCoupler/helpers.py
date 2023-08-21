import sys
sys.path.append('../')
from generic_device.generic_parameter import GenericParameter

from twisted.internet.defer import inlineCallbacks
from labrad.wrappers import connectAsync

from conductor_device.conductor_parameter import ConductorParameter

from motion.calibrated_picomotor import CalibratedPicomotor
import numpy as np
import time

class FiberCouplerDevice(ConductorParameter):
    """
    Device for automatic fiber coupling.
    """
    priority = 4

    def __init__(self, controller_id, labjack_channel, setpoint_var, calibration, config={}):
        super(FiberCouplerDevice, self).__init__(config)

        self.controller_id = controller_id
        self.labjack_channel = labjack_channel
        self.setpoint_var = setpoint_var
        self.calibration = calibration

        self.min_power = 0.6
    
    @inlineCallbacks
    def initialize(self):
        self.cxn = yield connectAsync()
        try:
            self.picomotor = self.cxn.polarkrb_picomotor
            self.labjack = self.cxn.polarkrb_labjack
            self.conductor = self.cxn.conductor
            self.picomotor.select_device(self.controller_id)
            self.signal_source = lambda: self.labjack.read_name(self.labjack_channel)
            self.cpm = CalibratedPicomotor(self.picomotor, signal_source=self.signal_source, calibration=self.calibration)

        except AttributeError as e:
            # Log a warning that the server can't be found.
            # Conductor will throw an error and remove the parameter
            raise Exception("Could iniitalize fiber coupler device {}: {}".format(self.controller_id, e))

    @inlineCallbacks
    def update(self):
        if self.value and "optimize" in self.value:
            try:
                # TODO: Make sure the MOT is turned on, possibly using sequencer.run_sequence

                params = yield self.conductor.get_parameter_values()
                setpoint = params["sequencer"][self.setpoint_var]
                current_value = self.signal_source()
                if current_value > setpoint:
                    return
                if current_value < self.min_power:
                    raise Exception("Power too low to optimize, aborting")
                
                def line_scan(axis, start, end, npoints):
                    positions = np.linspace(start, end, npoints) + self.cpm.get_position(axis)
                    voltages = np.zeros(npoints)
                    for (i, position) in enumerate(positions):
                        self.cpm.move_abs(axis, position)
                        voltages[i] = self.signal_source()
                    best_position = positions[np.argmax(voltages)]
                    self.cpm.move_abs(axis, best_position)
                    return best_position, self.signal_source()
                
                t = time.time()

                ranges = [50]*20
                last_side = {axis: 0 for axis in self.cpm.axes} # -1 for negative, 0 for none, 1 for positive
                best_voltage = -10
                rounds_since_best = 0
                for (round_num, max_delta) in enumerate(ranges):
                    for axis in self.cpm.axes:
                        # if the power is too low, do nothing to avoid misalignment
                        if self.signal_source() < self.min_power:
                            raise Exception('Power is too low, aborting')

                        start_position = self.cpm.get_position(axis)
                        if last_side[axis] < 0:
                            best_position, max_voltage = line_scan(axis, 0, -max_delta, 5)
                        elif last_side[axis] > 0:
                            best_position, max_voltage = line_scan(axis, 0, max_delta, 5)
                        else:
                            best_position, max_voltage = line_scan(axis, - max_delta, + max_delta, 7)
                        print("Axis {} round {}: position {}, voltage {}".format(axis, round_num, best_position, max_voltage))
                        if np.abs((best_position - start_position)/max_delta) > 0.8:
                            last_side[axis] = np.sign(best_position - start_position)
                        else:
                            last_side[axis] = 0

                    v = self.signal_source()
                    if v > best_voltage:
                        best_voltage = v
                        rounds_since_best = 0
                    else:
                        rounds_since_best += 1
                    if rounds_since_best > 3:
                        break

                final_voltage = self.signal_source()
                print("Alignment took {} seconds".format(time.time() - t))
                print("Final voltage: {}".format(final_voltage))

                if final_voltage < setpoint:
                    raise Exception("Alignment failed, aborting. Final voltage was {} but setpoint was {}".format(final_voltage, setpoint))
                
            except Exception as e:
                raise(e)
