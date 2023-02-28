import synthesizer_sequences as ss
from math import pi

seq = [ss.SetTransition(ss.Transition(1E6, [0.5], [1000]))] + ss.XY16(1.0, pulse=ss.PiPulse(centered=True, window=ss.GaussianPulse))
# seq = [
#     [ss.SetTransition(ss.Transition(1E6, [0.5], [1000]))] + ss.KDD(1.0, pulse=ss.PiPulse(centered=True, window=ss.GaussianPulse)),
#     [ss.SetTransition(ss.Transition(1E6, [0.5], [1000]))] + ss.XY16(1.0, pulse=ss.PiPulse(centered=True, window=ss.GaussianPulse))
# ]

print(ss.compile_sequence(seq, False)[0])

server.write_timestamps(None, ss.compile_sequence(seq, True)[0], 0)

ss.plot_sequence(seq)

# ts = server.compile_timestamp(
#     0, # channel
#     0, # address
#     0, # timestamp
#     True, # phase_update
#     0, # phase
#     0, # amplitude
#     0, # frequency
#     False # wait_for_trigger
# )

# for s in ts:
#     print(s.hex())