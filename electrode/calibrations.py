# E Field Calibration
# EFC = {
# 	'LP' : {'m' : -2000, 'b': 0},
# 	'UP' : {'m' : -2000, 'b': 0},
# 	'LW' : {'m' : -2000, 'b': 0},
# 	'LE' : {'m' : -2000, 'b': 0},
# 	'UW' : {'m' : -2000, 'b': 0},
# 	'UE' : {'m' : -2000, 'b': 0}
# }

EFC = {
	'LP' : {'m' : -2001.27, 'b': -0.527},
	'UP' : {'m' : -2001.16, 'b': -0.481},
	'LW' : {'m' : -2001.19, 'b': -0.439},
	'LE' : {'m' : -1999.84, 'b': -0.354},
	'UW' : {'m' : -2001.18, 'b': -0.453},
	'UE' : {'m' : -2000.11, 'b': -0.371}
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
