import labrad
import time


cxn = labrad.connect()
s = cxn.polarkrb_picomotor

s.select_device(s.get_device_list()[0])
# s.reinit_connection()
# s.reset()


# converts a note (e.g 'A4') to a frequency in Hz
def note_to_Hz(note):
    if note == 'R':
        return 0
    note = note.upper()
    notes = {'C': 0, 'C#': 1, 'D': 2, 'D#': 3, 'E': 4, 'F': 5, 'F#': 6,
             'G': 7, 'G#': 8, 'A': 9, 'A#': 10, 'B': 11}
    octave = int(note[-1])
    note = note[:-1]
    return round(440 * 2**((octave-4) + (notes[note])/12))

# La Marsellaise
notes = [('C4',1/16), ('C4',3/16), ('C4',1/16), ('F4',1/4), ('F4',1/4), ('G4',1/4), ('G4',1/4), ('C5',3/8), ('A4',1/8), ('F4',3/16), ('F4',1/16), ('A4',3/16), ('F4',1/16), ('D4',1/4), ('B4',1/2), ('G4',3/16), ('E4',1/16), ('F4',1/4), ('R',1/4), ('F4', 3/16), ('G4',1/8), ('A4',1/4), ('A4', 1/4), ('A4', 1/4), ('B4',3/16), ('A4',1/16),('A4',1/4), ('G4',1/4),('R',1/4),('G4',3/16),('A4',1/16),('B4',1/4),('B4',1/4),('B4',1/4),('C4',3/16),('B4',1/16),('A4',1/2)]

sign = 1
for note, duration in notes:
    vel = note_to_Hz(note)
    s.set_velocity(1, vel)
    time.sleep(0.02)
    s.move_rel(1, sign * 50)
    time.sleep(duration)
    s.abort()
    time.sleep(0.02)
    print('moving at {} Hz for {} steps'.format(vel, int(sign*vel/duration)))
    sign *= -1
