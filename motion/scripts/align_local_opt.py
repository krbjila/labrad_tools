import labrad
import numpy as np
from matplotlib import pyplot as plt

#### ### ### ####
optimize_Rb = False
# Optimizes K if False
#### ### ### ####

import os, sys

sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), ".."))
from calibrated_picomotor import CalibratedPicomotor
import time

cxn = labrad.connect()
picomotor = cxn.polarkrb_picomotor
labjack = cxn.polarkrb_labjack


if optimize_Rb:
    print("optimize Rb")

    def get_voltage():
        return labjack.read_name("AIN0")

    picomotor.select_device("RbMOT")
    calibration = {
        1: 1 / 0.9060735228939916,
        2: 1 / 0.8211087379097065,
        3: 1 / 0.921183140809069,
        4: 1 / 0.873316437926352,
    }
else:

    def get_voltage():
        return labjack.read_name("AIN1")

    picomotor.select_device("KMOT")
    calibration = {
        1: 1.2430034558945282,
        2: 1.2012205752414258,
        3: 1.0936954742350635,
        4: 1.1944678217819649,
    }

cpm = CalibratedPicomotor(
    picomotor, signal_source=get_voltage, calibration=calibration, velocity=2000
)
# cpm.axes = [1,4]
# cpm.axes = [2,3]

for axis in cpm.axes:
    cpm.positions[axis] = 0


def line_scan(axis, start, end, npoints):
    positions = np.linspace(start, end, npoints) + cpm.get_position(axis)
    voltages = np.zeros(npoints)
    for i, position in enumerate(positions):
        cpm.move_abs(axis, position)
        voltages[i] = get_voltage()
    best_position = positions[np.argmax(voltages)]
    cpm.move_abs(axis, best_position)
    return best_position, get_voltage()


# plt.ion()
fig = plt.figure()
ax = fig.add_subplot(1, 1, 1)
fig.canvas.draw()
background = fig.canvas.copy_from_bbox(ax.bbox)
plt.show(block=False)

xs = []
ys = []
(line,) = ax.plot(xs, ys, "o-")

# move to a random position
# for axis in cpm.axes:
#     cpm.move_rel(axis, np.random.randint(-200, 200))

t = time.time()

ranges = [50] * 50
last_side = {
    axis: 0 for axis in cpm.axes
}  # -1 for negative, 0 for none, 1 for positive
best_voltage = -10
rounds_since_best = 0
for round_num, max_delta in enumerate(ranges):
    for axis in cpm.axes:
        # if the power is too low, do nothing to avoid misalignment
        if get_voltage() < 0.1:
            print("Power is too low, aborting")
            exit(69420)

        start_position = cpm.get_position(axis)
        if last_side[axis] < 0:
            best_position, max_voltage = line_scan(axis, 0, -max_delta, 5)
        elif last_side[axis] > 0:
            best_position, max_voltage = line_scan(axis, 0, max_delta, 5)
        else:
            best_position, max_voltage = line_scan(axis, -max_delta, +max_delta, 7)
        print(
            "Axis {} round {}: position {}, voltage {}".format(
                axis, round_num, best_position, max_voltage
            )
        )
        if np.abs((best_position - start_position) / max_delta) > 0.8:
            last_side[axis] = np.sign(best_position - start_position)
        else:
            last_side[axis] = 0
    v = get_voltage()
    xs.append(round_num)
    ys.append(v)

    line.set_data(xs, ys)
    ax.set_xlim(xs[0], xs[-1])
    ax.set_ylim(min(ys), max(ys))
    fig.canvas.restore_region(background)
    ax.draw_artist(line)
    fig.canvas.blit(ax.bbox)
    fig.canvas.flush_events()

    if v > best_voltage:
        best_voltage = v
        rounds_since_best = 0
    else:
        rounds_since_best += 1
    if rounds_since_best > 3:
        break

# ranges = [50]
# for (round_num, max_delta) in enumerate(ranges):
#     for axis in cpm.axes:
#         last_side = 0 # -1 for negative, 0 for none, 1 for positive
#         for move in range(50): # set a maximum number of moves
#             start_position = cpm.get_position(axis)
#             if last_side < 0:
#                 best_position, max_voltage = line_scan(axis, 0, -max_delta, 3)
#             elif last_side > 0:
#                 best_position, max_voltage = line_scan(axis, 0, max_delta, 3)
#             else:
#                 best_position, max_voltage = line_scan(axis, - max_delta, + max_delta, 7)
#             print("Axis {} round {}: position {}, voltage {}".format(axis, round_num, best_position, max_voltage))
#             voltage_history.append(max_voltage)
#             # line.set_ydata(voltage_history)
#             # fig.canvas.draw()
#             # fig.canvas.flush_events()
#             if np.abs((best_position - start_position)/max_delta) < 0.8:
#                 break
#             last_side = np.sign(best_position - start_position)

print("It takes {:.2f} s".format(time.time() - t))
print("Final voltage: {}".format(get_voltage()))
