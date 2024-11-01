import labrad
import json

servername = 'krbg2_dds'

sequence = {
	'3xAD9959_0' : [
		{'name' : 'New Up Leg Experiment', 'address' : [0,0], 'frequency' : 80.0},
		{'name' : 'Up Leg Experiment', 'address' : [0,1], 'frequency' : 43.0},
		{'name' : 'New Down Leg Experiment', 'address' : [0,2], 'frequency' : 200.0},
		{'name' : 'Down Leg Experiment', 'address' : [0,3], 'frequency' : 80.0}, # Drives Down Leg Expt, Master-Slave beat
		{'name' : 'Vertical Lattice', 'address' : [1,0], 'frequency' : 90.0},
		{'name' : 'Horizontal OT', 'address' : [1,1], 'frequency' : 110.0},
		{'name' : 'MARIA OT', 'address' : [1,2], 'frequency' : 70.0},
		{'name' : 'Plug Beam', 'address' : [1,3], 'frequency' : 80.0},
		{'name' : 'K D1 AOM', 'address' : [2,0], 'frequency' : 80.0},
		{'name' : 'H. Lattice 1', 'address' : [2,1], 'frequency' : 70.0},
		{'name' : 'H. Lattice 2', 'address' : [2,2], 'frequency' : 110.0},
		{'name' : 'Fat Latt AKA Large Spacing Lattice', 'address' : [2,3], 'frequency' : 90.0}
	]
}

cxn = labrad.connect()
server = cxn.servers[servername]
server.update_dds(json.dumps(sequence))