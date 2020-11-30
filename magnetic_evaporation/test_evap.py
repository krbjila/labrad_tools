from __future__ import print_function
import visa
from time import sleep, time
from evaporate import evaporation

rm = visa.ResourceManager('@py')


def do_evap(evap, device):
	print("Total evaporation time is {:0.1f}s".format(evap.totaltime))

	cmds = []
	for k in range(evap.points):
		cmds.append('FREQ {:0.2f}kHz; VOLT {:0.2f}dbm;'.format(evap.trajectory[k],evap.amps[k]))	
	
	asg = rm.open_resource(device)
	asg.write("FUNC SIN; VOLT:OFFS 0V")
	asg.write("OUTP:STAT ON")
	for k in cmds:
		asg.write(k)
		sleep(evap.dt)
	asg.write("OUTP:STAT OFF")
	asg.close()

device = 'GPIB0::9::INSTR'
do_evap(evaporation(), device)
