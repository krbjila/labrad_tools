from math import pi

import sys, os
current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)
import synthesizer_sequences as ss

s1 = [ss.SetTransition(ss.Transition(2E6, [0.5], [1000]))] + ss.XY16(1.0, pulse=ss.PiPulse(centered=True, window=ss.RectangularPulse))
# seq = [
#     [ss.SetTransition(ss.Transition(1E6, [0.5], [1000]))] + ss.KDD(1.0, pulse=ss.PiPulse(centered=True, window=ss.GaussianPulse)),
#     [ss.SetTransition(ss.Transition(1E6, [0.5], [1000]))] + ss.XY16(1.0, pulse=ss.PiPulse(centered=True, window=ss.GaussianPulse))
# ]

seq = [
    [ss.Timestamp(1/3, 1, 0, 1E6), ss.Timestamp(1/3, 0.5, pi, 1E6, digital_out={0:True}), ss.Timestamp(1/3, 0.5, pi, 1E6, digital_out={0:False})],
    s1
]

print(ss.compile_sequence(seq))

ss.plot_sequence(seq)