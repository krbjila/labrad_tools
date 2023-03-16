from math import pi

import sys, os
current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)
import synthesizer_sequences as ss

seq = [ss.SetTransition(ss.Transition(1E6, [0.5], [1000]))] + ss.XY16(1.0, pulse=ss.PiPulse(centered=True, window=ss.GaussianPulse))
# seq = [
#     [ss.SetTransition(ss.Transition(1E6, [0.5], [1000]))] + ss.KDD(1.0, pulse=ss.PiPulse(centered=True, window=ss.GaussianPulse)),
#     [ss.SetTransition(ss.Transition(1E6, [0.5], [1000]))] + ss.XY16(1.0, pulse=ss.PiPulse(centered=True, window=ss.GaussianPulse))
# ]

print(ss.compile_sequence(seq, False)[0])

ss.plot_sequence(seq)