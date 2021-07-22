tx_types_dictionary = {
	'single': 0,
	'drLimits': 1,
	'drStepSize': 2,
	'drRate': 3,
	'sweepInvert': 4 # send 0 for no invert, 1 for invert
}

SYSCLK = 1000 # MHz

def calcFTW(freq):
	"""
	calcFTW(freq)

	Returns string of bytes MSB in format "byte_3,byte_2,byte_1,byte_0,"

	Args:
		freq (float): frequency in MHz

	Returns:
		str: string of bytes MSB in format "byte_3,byte_2,byte_1,byte_0,"
	"""
	FTW = int(2**(32) * float(freq) / SYSCLK)
	# Format string MSB first
	hex_str = '{:08X}'.format(FTW)
	res = ""
	for i in range(0, 4):
		res = res + "0x" + hex_str[2*i:(2*i+2)] + ","
	return res

def calcPOW(phase):
	"""
	calcPOW(phase)

	Returns string of bytes MSB in format "byte_1,byte_0,"

	Args:
		phase (float): phase in degrees

	Returns:
		str: string of bytes MSB in format "byte_1,byte_0,"
	"""
	phase = phase % 360
	POW = int(2**(16) * float(phase) / 360)

	# Format string
	hex_str = '{0:04X}'.format(POW)
	res = ""
	for i in range(0,2):
		res = res + "0x" + hex_str[2*i:(2*i + 2)] + ","
	return res

def calcAMPL(ampl):
	"""
	calcAMPL(ampl)

	Returns string of bytes MSB in format "byte_1,byte_0,"

	Args:
		ampl (float): relative amplitude in dB relative to full scale. Range is 0 to -80 dB.

	Returns:
		str: string of bytes MSB in format "byte_1,byte_0,"
	"""
	# Upper limit is 0 dB
	if ampl >= 0:
		return "0x3F,0xFF,"
	# Lower limit is -80 dB
	elif ampl < -80:
		ampl = -80

	AMPL = int(2**(14) * pow(10, float(ampl)/20))
	hex_str = '{0:04X}'.format(AMPL)
	res = ""
	for i in range(0,2):
		res = res + "0x" + hex_str[2*i:(2*i + 2)] + ","
	return res

def calcStepInterval(interval):
	"""
	calcStepInterval(interval)

	Returns string of bytes MSB in format "byte_1,byte_0,"

	Args:
		interval (float): step interval in microseconds

	Returns:
		str: Returns string of bytes MSB in format "byte_1,byte_0,"
	"""
	min_interval = float(4) / SYSCLK
	max_interval = (2**(16) - 1) * min_interval
	if (interval < min_interval):
		interval = min_interval
	elif (interval > max_interval):
		interval = max_interval

	intW = int(interval / min_interval)
	# Format string
	hex_str = '{0:04X}'.format(intW)
	res = ""
	for i in range(0,2):
		res = res + "0x" + hex_str[2*i:(2*i + 2)] + ","
	return res

def calcRampParameters(start, stop, dt, nsteps=1000):
	"""
	calcRampParameters(start, stop, dt, nsteps=1000)

	Calculates ramp parameters

	Args:
		start (float): start frequency in MHz
		stop (float): stop frequency in MHz
		dt (float): duration in milliseconds
		nsteps (int, optional): number of steps in sweep. Defaults to 1000.

	Returns:
		dict: Dictionary with items:
			upper: upper limit frequency in MHz
			lower: lower limit frequency in MHz
			slope: slope polarity (+1 for positive ramp, -1 for negative ramp)
			interval: step interval for accumulator in microseconds
			step: frequency change per step in MHz
	"""
	slope = 0
	if start <= stop:
		slope = 1
		lower = start
		upper = stop
	else:
		slope = -1
		lower = stop
		upper = start

	# dt is given in ms
	# Convert to microseconds
	# To get dt per step, divide by nsteps
	# This is step interval in microseconds
	dt_each = 1000 * float(dt) / nsteps
	df_each = float(upper - lower) / nsteps

	# DRG automatically starts from lower limit
	# If slope is negative, need to do something fancy
	if slope == 1:
		p_interval = dt_each
		n_interval = 0 # minimum step interval
		p_step = df_each
		n_step = df_each
	elif slope == -1:
		p_interval = 0 # minimum step interval; quickly sweep up to upper limit
		n_interval = dt_each
		p_step = float(df_each) * nsteps # positive step size is the whole sweep interval
		n_step = df_each
	return {'upper': upper, 'lower': lower, 'slope': slope, 'p_interval': p_interval, 'n_interval': n_interval, 'p_step': p_step, 'n_step': n_step}