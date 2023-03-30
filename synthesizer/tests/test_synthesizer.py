import sys, os
current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)
import synthesizer_sequences as ss
import labrad
import jsonpickle, pprint

from math import pi

# seq = [
#     [ss.SetTransition(ss.Transition(10E6, [0.5], [1E5]))] + ss.XY16(0.005, pulse=ss.PiPulse(centered=True, window=ss.GaussianPulse))
# ]

# seq = [
#     [ss.Timestamp(1E-3, 1, 0, 10E6, absolute_phase=True), ss.Timestamp(3, None, None, None)],
#     [ss.Timestamp(1E-3, 1, 0, 10E6, absolute_phase=True), ss.PhaseRamp(3, None, 0, 2*pi, None, 51)]
# ]

# seq = [[],[],[],[], []]

seq = [
    ss.Timestamp(1, (i+1)/7, None, 10E6, digital_out={i: True, (i-1) % 7:False})
    for i in range(7)
] + [ss.Timestamp(1, 0, None, 10E6, digital_out={i: False for i in range(7)})]
ss.plot_sequence(seq)

# compiled, durations = ss.compile_sequence(seq)
# pp = pprint.PrettyPrinter(indent=4)
# pp.pprint(jsonpickle.loads(compiled))

cxn = labrad.connect()
cxn.polarkrb_synthesizer.write_timestamps(jsonpickle.dumps(seq, keys=True), True, False)
cxn.polarkrb_synthesizer.trigger()