from math import pi

import sys, os
import json

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)
import synthesizer_sequences as ss

seq = {
    0: [
        ss.SetTransition(ss.Transition(2E6, {0.5: 100E3})),
        # ss.DROID60(2.4E-3)
        ss.KDD(2.4E-3)
        ],
}

compiled, durations = ss.compile_sequence(seq, True)
for s in compiled[0][0:-1]:
    print(s)
print("durations: {}".format(durations))

#Save compiled as a json file
with open('compiled.json', 'w') as outfile:
    json.dump(json.loads(compiled), outfile, indent=4, sort_keys=True)

compiled, durations, fig = ss.plot_sequence(seq)
# fig.write_html("fig.html")
