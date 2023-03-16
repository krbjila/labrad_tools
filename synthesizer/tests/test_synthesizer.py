import sys, os
current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)
import synthesizer_sequences as ss
import labrad
import json, pprint

# seq = [
#     [ss.SetTransition(ss.Transition(1E6, [0.5], [1000]))] + ss.XY16(0.25, pulse=ss.PiPulse(centered=True, window=ss.GaussianPulse))
# ]

# seq[0][0].wait_for_trigger = True

seq = [
    ss.Timestamp(1, 1, 0, 1E6),
    ss.Timestamp(1, 0.5, None, 1E6),
    ss.Timestamp(1, 0, None, 1E6)
]
# ss.plot_sequence(seq)

compiled, durations = ss.compile_sequence(seq)
pp = pprint.PrettyPrinter(indent=4)
pp.pprint(json.loads(compiled))

cxn = labrad.connect()
cxn.krbg2_synthesizer.write_timestamps(compiled)