# E Field Calibration
EFC = {
	'LP' : {'m' : -2001.71,'b' : -0.556},
	'UP' : {'m' : -2001.78, 'b': 1.260},
	'LW' : {'m' : -2002.05, 'b': 3.126},
	'LE' : {'m' : -2001.36, 'b': -6.276},
	'UW' : {'m' : -2000.16, 'b': -2.564},
	'UE' : {'m' : -2002.04, 'b': 0.18}
}

ZEROS = {x : -EFC[x]['b']/EFC[x]['m'] for x in EFC.keys()}

# Plate separation used to calculate E field
PLATE_SEPARATION = 0.6 # cm

# Fudge factor away from parallel plate capacitor
RODS_CORRECTION = 0.955

# Safety limit for DACs; HV is limited to 2000x this value
DAC_LIMIT = 2

# Default comp shim
COMP_SHIM_DEFAULT = 1.5