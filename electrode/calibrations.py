# E Field Calibration
EFC = {
	'LP' : {'m' : -2001.16, 'b': -0.336},
	'UP' : {'m' : -2001.09, 'b': -0.309},
	'LW' : {'m' : -2001.11, 'b': -0.349},
	'LE' : {'m' : -1999.76, 'b': -0.221},
	'UW' : {'m' : -2001.10, 'b': -0.315},
	'UE' : {'m' : -2001.07, 'b': -0.323}
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
