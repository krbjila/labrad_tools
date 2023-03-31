from math import pi

import sys, os
current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)
import synthesizer_sequences as ss

seq = {
    0: [ss.SetTransition(ss.Transition(2E6, [0.5], [1000]))] + ss.XY16(1.0, pulse=ss.PiPulse(centered=True, window=ss.RectangularPulse)),
    2: [ss.SetTransition(ss.Transition(2E6, [0.5], [1000]))] + ss.XY16(1.0, pulse=ss.PiPulse(centered=True, window=ss.RectangularPulse))
}

print(ss.compile_sequence(seq))

ss.plot_sequence(seq)
