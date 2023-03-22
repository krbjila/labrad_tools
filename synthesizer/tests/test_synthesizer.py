import sys, os
current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)
import synthesizer_sequences as ss
import labrad
import json, pprint

from math import pi

# seq = [
#     [ss.SetTransition(ss.Transition(1E6, [0.5], [1000]))] + ss.XY16(0.25, pulse=ss.PiPulse(centered=True, window=ss.GaussianPulse))
# ]

# seq[0][0].wait_for_trigger = True

seq = [
    [ss.Timestamp(1E-3, 1, 0, 1E6, absolute_phase=True), ss.Timestamp(3, 1, 0, 1E6)],
    [ss.Timestamp(1E-3, 1, 0, 1E6, absolute_phase=True), ss.PhaseRamp(3, 1, 0, 2*pi, 1E6, 51)]
]

# seq = [
#     ss.Timestamp(0.001, (i+1)/7, None, 10E6, digital_out={i: True, (i-1) % 7:False})
#     for i in range(7)
# ] + [ss.Timestamp(0.001, 0, None, 10E6, digital_out={i: False for i in range(7)})]
ss.plot_sequence(seq)

compiled, durations = ss.compile_sequence(seq)
pp = pprint.PrettyPrinter(indent=4)
pp.pprint(json.loads(compiled))

cxn = labrad.connect()
cxn.krbg2_synthesizer.write_timestamps(compiled)