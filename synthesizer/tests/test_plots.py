from math import pi

import sys, os
current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)
import synthesizer_sequences as ss

seq = {
    0: [ss.SetTransition(ss.Transition(2E6, [0.5], [1000])), ss.BB1(pi)],
}

compiled, durations = ss.compile_sequence(seq, False)
for s in compiled[0][0:-1]:
    print(s)
print("durations: {}".format(durations))

ss.plot_sequence(seq)
