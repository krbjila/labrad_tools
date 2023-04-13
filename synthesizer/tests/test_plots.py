from math import pi

import sys, os
current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)
import synthesizer_sequences as ss

seq = {
    0: [
        ss.SetTransition(ss.Transition(2E6, [0.5], [100E3])),
        ss.PiOver2Pulse(window=ss.BB1),
        ss.KDD(2E-3, ss.BB1(pi, window=ss.GaussianPulse)),
        ss.PiOver2Pulse(phase=pi/2, window=ss.BB1)
        ],
}

compiled, durations = ss.compile_sequence(seq, False)
for s in compiled[0][0:-1]:
    print(s)
print("durations: {}".format(durations))

compiled, durations, fig = ss.plot_sequence(seq)
# fig.write_html("fig.html")
