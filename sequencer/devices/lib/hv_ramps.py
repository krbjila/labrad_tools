import numpy as np

V_MAX = 4.8

def H(x):
    """
    step function
    """
    return 0.5*(np.sign(x-1e-9)+1)

def G(t1, t2):
    """
    pulse
    """
    return lambda t: H(t2-t) - H(t1-t) 

def round_dt(dt):
    return float('{0:.7f}'.format(dt))
#    return dt

def round_dv(dv):
    return float('{0:.7f}'.format(dv))
#    return dv

def lin_ramp(p):
    """
    returns continuous finction defined over ['ti', 'tf'].
    values are determined by connecting 'vi' to 'vf' with a line.
    """
    return lambda t: G(p['ti'], p['tf'])(t)*(p['vi'] + (p['vf']-p['vi'])/(p['tf']-p['ti'])*(t-p['ti']))

def exp_ramp(p, ret_seq=False):
    """
    returns continuous finction defined over ['ti', 'tf'].
    values are determined by connecting 'vi' to 'vf' with an exponential function.
    v = a*e^{-t/'tau'} + c
    """
    p['a'] = (p['vf']-p['vi'])/(np.exp(p['dt']/p['tau'])-1)
    p['c'] = p['vi'] - p['a']
    v_ideal = lambda t: G(p['ti'], p['tf'])(t)*(p['a']*np.exp((t-p['ti'])/p['tau']) + p['c'])
    t_pts = np.linspace(p['ti'], p['tf']-2e-9, p['pts']+1)
    v_pts = v_ideal(t_pts)
    sseq = [{'type': 'lin', 'ti': ti, 'tf': tf, 'vi': vi, 'vf': vf} 
            for ti, tf, vi, vf in zip(t_pts[:-1], t_pts[1:], v_pts[:-1], v_pts[1:])]
    if ret_seq:
        return sseq
    else:
        return lambda t: sum([lin_ramp(ss)(t) for ss in sseq])

class SRamp(object):
    required_parameters = [
        ('vf', ([-V_MAX, V_MAX], [(0, 'V'), (-3, 'mV')], 3)),
        ('dt', ([1e-6, 50], [(0, 's'), (-3, 'ms'), (-6, 'us')], 1)), 
        ]
    def __init__(self, p=None):
        self.p = p
        if p is not None:
            p['vi'] = p['vf']
            self.v = lin_ramp(p)

    def to_lin(self):
        """
        to list of linear ramps [{dt, dv}]
        """
        p = self.p
        return [{'dt': 1e-6, 'dv': p['vf'] - p['_vi']}, {'dt': p['dt']-1e-6, 'dv': 0}]

class LinRamp(object):
    required_parameters = [
        ('vf', ([-V_MAX, V_MAX], [(0, 'V'), (-3, 'mV')], 3)),
        ('dt', ([1e-6, 50], [(0, 's'), (-3, 'ms'), (-6, 'us')], 1)), 
        ]
    def __init__(self, p=None):
        self.p = p
        if p is not None:
            self.v = lin_ramp(p)

    def to_lin(self):
        """
        to list of linear ramps [{dt, dv}]
        """
        p = self.p
        return [{'dt': p['dt'], 'dv': p['vf']-p['_vi']}]

class SLinRamp(object):
    required_parameters = [
        ('vi', ([-V_MAX, V_MAX], [(0, 'V'), (-3, 'mV')], 3)),
        ('vf', ([-V_MAX, V_MAX], [(0, 'V'), (-3, 'mV')], 3)),
        ('dt', ([1e-6, 50], [(0, 's'), (-3, 'ms'), (-6, 'us')], 1)), 
        ]
    def __init__(self, p=None):

        if p is not None:
            self.p = p
            self.v = lin_ramp(p)

    def to_lin(self):
        """
        to list of linear ramps [{dt, dv}]
        """
        p = self.p
        return [{'dt': 1e-6, 'dv': p['vi'] - p['_vi']}, {'dt': p['dt']-1e-6, 'dv': p['vf']-p['vi']}]

class ExpRamp(object):
    required_parameters = [
        ('vf', ([-V_MAX, V_MAX], [(0, 'V')], 3)),
        ('dt', ([1e-6, 50], [(0, 's'), (-3, 'ms'), (-6, 'us')], 1)), 
        ('tau', ([-1e2, 1e2], [(0, 's'), (-3, 'ms'), (-6, 'us'), (-9, 'ns')], 1)),
        ('pts', ([1, 100], [(0, 'na')], 0)),
        ]
    def __init__(self, p=None):
        self.p = p
        if p is not None:
            self.v = exp_ramp(p)

    def to_lin(self):
        """
        to list of linear ramps [{dt, dv}]
        """
        p = self.p
        seq = exp_ramp(p, ret_seq=True)
        return [{'dt': round_dt(s['tf']-s['ti']), 'dv': round_dv(s['vf']-s['vi'])} for s in seq]

class SExpRamp(object):
    required_parameters = [
        ('vi', ([-V_MAX, V_MAX], [(0, 'V')], 3)),
        ('vf', ([-V_MAX, V_MAX], [(0, 'V')], 3)),
        ('dt', ([1e-6, 50], [(0, 's'), (-3, 'ms'), (-6, 'us')], 1)), 
        ('tau', ([-1e2, 1e2], [(0, 's'), (-3, 'ms'), (-6, 'us')], 1)),
        ('pts', ([1, 100], [(0, 'na')], 0)),
        ]
    def __init__(self, p=None):
        self.p = p
        if p is not None:
            self.v = exp_ramp(p)
    
    def to_lin(self):
        """
        to list of linear ramps [{dt, dv}]
        """
        p = self.p
        seq = exp_ramp(p, ret_seq=True)
        return [{'dt': 1e-6, 'dv': p['vi']-p['_vi']}] + [{'dt': s['tf']-s['ti'], 'dv': s['vf']-s['vi']} for s in seq]

class hvRampMaker(object):
    available_ramps = {
        's': SRamp,
        'lin': LinRamp,
        'slin': SLinRamp,
        'exp': ExpRamp,
        'sexp': SExpRamp,
        }
    def __init__(self, sequence):
        j=0
        for i, s in enumerate(sequence):
            if s['type'] is 'sub':
                seq = sequence.pop(i+j)['seq']
                for ss in s['seq']:
                    sequence.insert(i+j, ss)
                    j += 1
        
        sequence[0]['_vi'] = 0
        for i in range(len(sequence)-1):
            sequence[i+1]['_vi'] = sequence[i]['vf']
        for i in range(len(sequence)):
            if not sequence[i].has_key('vi'):
                sequence[i]['vi'] = sequence[i]['_vi']
    
        for i, s in enumerate(sequence):
            s['ti'] = sum([ss['dt'] for ss in sequence[:i]])
            s['tf'] = s['ti'] + s['dt']
        
        self.v = lambda t: sum([self.available_ramps[s['type']](s).v(t) for s in sequence])
        self.sequence = sequence

    def get_plottable(self, scale='real', pts=100):
        T = np.concatenate([np.linspace(s['ti'], s['tf'], pts)[:-1] for s in self.sequence])
        V = self.v(T)
        if scale=='real':
            return T, V
        elif scale=='step':
            T = range(len(V))
            return T, V

    def get_continuous(self):
        return self.v

    def get_programmable(self):
        """
        to list of linear ramps [{dt, dv}]
        """
        lins = np.concatenate([self.available_ramps[s['type']](s).to_lin() for s in self.sequence]).tolist()
        return lins #combine_flat_ramps([], lins)

def combine_flat_ramps(l, s):
    if not l:
        l = [s.pop(0)]
    if s:
        nxt = s.pop(0)
        if nxt['dv'] == 0 and l[-1]['dv'] == 0:
            l[-1]['dt'] += nxt['dt']
            return combine_flat_ramps(l, s)
        else:
            return l + combine_flat_ramps([nxt], s)
    else:
        return l
