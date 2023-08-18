import numpy as np
from scipy.optimize import minimize
from matplotlib import pyplot as plt
import time

class CalibratedPicomotor():
    def __init__(self, picomotor, calibration=None, positions=None, signal_source=None, velocity=2000):
        self.picomotor = picomotor
        self.calibration = calibration
        self.axes = [1, 2, 3, 4]

        self.velocity = velocity
        for axis in self.axes:
            self.picomotor.set_velocity(axis, self.velocity)
            time.sleep(0.1)

        if positions is None:
            positions = {axis: picomotor.get_position(axis) for axis in self.axes}
        self.positions = positions

        if calibration is None:
            if signal_source is None:
                raise ValueError("Must provide either calibration or signal_source for self-calibration")
            self.calibration = {axis: self._calibrate(axis, signal_source) for axis in self.axes}

    def get_position(self, axis):
        return self.positions[axis]
    
    def move_abs(self, axis, position):
        if position == self.positions[axis]:
            return
        delta_position = position - self.positions[axis]
        if self.calibration is not None and delta_position < 0:
            delta_position *= self.calibration[axis]
        self.picomotor.move_rel(axis, round(delta_position))
        time.sleep(abs(delta_position) / self.velocity + 0.04)
        self.positions[axis] = position

    def move_rel(self, axis, delta_position):
        if delta_position == 0:
            return
        self.positions[axis] += delta_position
        if self.calibration is not None and delta_position < 0:
            delta_position *= self.calibration[axis]
        self.picomotor.move_rel(axis, round(delta_position))
        time.sleep(abs(delta_position) / self.velocity + 0.04)

    def _calibrate(self, axis, signal_source):
        """Calibrates the step size of a picomotor axis.

        Args:
            axis (int): The axis to calibrate. Must be 1, 2, 3, or 4.
            signal_source (function): A function that returns the signal to use for calibration, which should change as a function of real position.

        Returns:
            float: The ratio of the forward and reverse step sizes of the picomotor.
        """
        x0 = self.positions[axis]
        positions = np.arange(x0-300, x0+300, 10)
        forward_voltages = np.zeros(len(positions))

        for (i, position) in enumerate(positions):
            self.move_abs(axis, position)
            forward_voltages[i] = signal_source()

        reverse_voltages = np.zeros(len(positions))
        for (i, position) in enumerate(np.flip(positions)):
            self.move_abs(axis, position)
            reverse_voltages[-i-1] = signal_source()

        def rescale_positions(scale):
            return positions[-1] + scale * (positions - positions[-1])
        
        def cost(scale):
            rescaled_positions = rescale_positions(scale)
            valid_range = (max(min(positions), min(rescaled_positions)), min(max(positions), max(rescaled_positions)))

            # make a sorted version of the positions and voltages for interpolation
            sort_indices = np.argsort(positions)

            x = np.linspace(valid_range[0], valid_range[1], 10)
            forward_voltages_interp = np.interp(x, positions[sort_indices], forward_voltages[sort_indices], left=None, right=None)
            reverse_voltages_interp = np.interp(x, rescaled_positions[sort_indices], reverse_voltages[sort_indices], left=None, right=None)
            res = np.sum((forward_voltages_interp - reverse_voltages_interp)**2)
            return res
        
        res = minimize(cost, [1])

        return res.x[0]
