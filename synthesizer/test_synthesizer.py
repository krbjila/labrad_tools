from math import pi
import labrad
import json
import time

cxn = labrad.connect()
synth = cxn.krbg2_synthesizer

program0 = [
    {
        "timestamp": 0,
        "phase_update": True,
        "phase": 0,
        "amplitude": 1,
        "frequency": 1E6
    },
    {
        "timestamp": 1,
        "phase_update": False,
        "phase": 0,
        "amplitude": 0.5,
        "frequency": 1E6
    },
    {
        "timestamp": 0,
        "phase_update": False,
        "phase": 0,
        "amplitude": 0,
        "frequency": 0
    }
]
program1 = [
    {
        "timestamp": 0,
        "phase_update": True,
        "phase": 0,
        "amplitude": 1,
        "frequency": 1.1E6
    },
    {
        "timestamp": 1,
        "phase_update": False,
        "phase": 0,
        "amplitude": 0.5,
        "frequency": 2E6
    },
    {
        "timestamp": 0,
        "phase_update": False,
        "phase": 0,
        "amplitude": 0,
        "frequency": 0
    }
]

print("Resetting synthesizer")
synth.reset()
time.sleep(2)

print("Writing timestamps")
synth.write_timestamps(json.dumps(program0), 0)
synth.write_timestamps(json.dumps(program1), 1)
synth.write_timestamps(json.dumps(program0), 2)
synth.write_timestamps(json.dumps(program1), 3)

time.sleep(1)

print('Triggering device')
synth.trigger()