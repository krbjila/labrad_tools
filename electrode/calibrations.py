# E Field Calibration
EFC = {
	'LP' : {'m' : -2001.233, 'b': -0.121},
	'UP' : {'m' : -2001.098, 'b': -0.023},
	'LW' : {'m' : -2001.235, 'b': -0.089},
	'LE' : {'m' : -1999.804, 'b': -0.027},
	'UW' : {'m' : -2001.111, 'b': -0.102},
	'UE' : {'m' : -2001.111, 'b': -0.112}
}

ZEROS = {x : -EFC[x]['b']/EFC[x]['m'] for x in EFC.keys()}

# Plate separation used to calculate E field
PLATE_SEPARATION = 0.6 # cm

# Fudge factor away from parallel plate capacitor
RODS_CORRECTION = 0.96079*1.01315

# Safety limit for DACs; HV is limited to 2000x this value
DAC_LIMIT = 2.5

# Default comp shim
COMP_SHIM_DEFAULT = 1.5

# Field we normalize comp_shim to
NORMALIZATION_FIELD = 3000.0
