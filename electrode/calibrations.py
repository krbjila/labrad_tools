# E Field Calibration
EFC = {
	'LP' : {'m' : -2001.63, 'b': 0.012},
	'UP' : {'m' : -2001.75, 'b': 2.245},
	'LW' : {'m' : -2001.97, 'b': 3.912},
	'LE' : {'m' : -1999.95, 'b': -4.048},
	'UW' : {'m' : -2001.31, 'b': -2.304},
	'UE' : {'m' : -2001.95, 'b': 1.793}
}

ZEROS = {x : -EFC[x]['b']/EFC[x]['m'] for x in EFC.keys()}

# Plate separation used to calculate E field
PLATE_SEPARATION = 0.6 # cm

# Fudge factor away from parallel plate capacitor
RODS_CORRECTION = 0.96079

# Safety limit for DACs; HV is limited to 2000x this value
DAC_LIMIT = 2

# Default comp shim
COMP_SHIM_DEFAULT = 1.5

# Field we normalize comp_shim to
NORMALIZATION_FIELD = 3000.0
