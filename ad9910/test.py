program = [
	# mode = 'single' or 'sweep'
	# start and stop in MHz
	# dt in milliseconds
	# nsteps is the number of total frequency steps in the sweep (1000 is default)
	# freq in MHz
	# ampl in dB relative to full scale (range: -80 to 0)
	# phase is phase offset in degrees
	{'mode': 'sweep', 'start': 9.4, 'stop': 7.6, 'dt': 30, 'nsteps': 10000},
#	{'mode': 'single', 'freq': 10, 'ampl': 0, 'phase': 0},
#	{'mode': 'sweep', 'start': 79.8, 'stop': 80.2, 'dt': .4, 'nsteps': 10000},

	#{'mode': 'single', 'freq': 80.001, 'ampl': 0, 'phase': 0},

#	{'mode': 'sweep', 'start': 10.7, 'stop': 8.7, 'dt': 10, 'nsteps': 1000},
#	{'mode': 'sweep', 'start': 80, 'stop': 80.1, 'dt': 0.1}
#	{'mode': 'single', 'freq': 0, 'ampl': 0, 'phase': 0},
]

profiles = [
	{'profile': 0, 'freq': 100, 'ampl': 0, 'phase': 0},
	{'profile': 1, 'freq': 200, 'ampl': 0, 'phase': 0},
	{'profile': 2, 'freq': 0, 'ampl': 0, 'phase': 0},
	{'profile': 3, 'freq': 0, 'ampl': 0, 'phase': 0},
	{'profile': 4, 'freq': 0, 'ampl': 0, 'phase': 0},
	{'profile': 5, 'freq': 0, 'ampl': 0, 'phase': 0},
	{'profile': 6, 'freq': 0, 'ampl': 0, 'phase': 0},
	{'profile': 7, 'freq': 0, 'ampl': 0, 'phase': 0},
]