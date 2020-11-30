from __future__ import print_function
import numpy as np

VLIM = 4

MIN_TIME = 1e-6


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
    try:
        p['a'] = (p['vf']-p['vi'])/(np.exp(p['dt']/p['tau'])-1)
    except Exception as e:
        print(e)
        sseq = [{'type': 'lin', 'ti': p['ti'], 'tf': p['tf'], 'vi': p['vi'], 'vf': p['vf']}]
        return lambda t: sum([lin_ramp(ss)(t) for ss in sseq])
    p['c'] = p['vi'] - p['a']
    v_ideal = lambda t: G(p['ti'], p['tf'])(t)*(p['a']*np.exp((t-p['ti'])/p['tau']) + p['c'])
    t_pts = np.linspace(p['ti'], p['tf']-2e-9, p['pts']+1)
    v_pts = v_ideal(t_pts)
    sseq = [{'type': 'lin', 'ti': ti, 'tf': tf, 'vi': vi, 'vf': vf} 
            for ti, tf, vi, vf in zip(t_pts[:-1], t_pts[1:], v_pts[:-1], v_pts[1:])]

    sseq[0]['vi'] = p['vi']
    sseq[-1]['vf'] = p['vf']

    if ret_seq:
        return sseq
    else:
        return lambda t: sum([lin_ramp(ss)(t) for ss in sseq])

def scurve_ramp(p, ret_seq=False):
    """
    returns continuous finction defined over ['ti', 'tf'].
    values are determined by connecting 'vi' to 'vf' with an exponential function.
    v = a / (1 + e^{-t/ 12 * 'tau'}) + c
    """
    p['a'] = p['vf']-p['vi']
    p['c'] = p['vi']

    t0 = (p['ti'] + p['tf']) / 2.0
    pdiff = (p['tf'] - p['ti'])
    steep = 12 * p['steep'] / pdiff # normalized, unitless

    v_ideal = lambda t: G(p['ti'], p['tf'])(t) * (p['a'] / (1 + np.exp(- (t - t0) * steep)) + p['c'])
    t_pts = np.linspace(p['ti'], p['tf']-2e-9, p['pts']+1)
    v_pts = v_ideal(t_pts)
    sseq = [{'type': 'lin', 'ti': ti, 'tf': tf, 'vi': vi, 'vf': vf} 
            for ti, tf, vi, vf in zip(t_pts[:-1], t_pts[1:], v_pts[:-1], v_pts[1:])]

    sseq[0]['vi'] = p['vi']
    sseq[-1]['vf'] = p['vf']

    if ret_seq:
        return sseq
    else:
        return lambda t: sum([lin_ramp(ss)(t) for ss in sseq])

class SRamp(object):
    required_parameters = [
        ('vf', ([-VLIM, VLIM], [(0, 'V'), (-3, 'mV')], 6)),
        ('dt', ([1e-6, 50], [(0, 's'), (-3, 'ms'), (-6, 'us')], 2)), 
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
        return [{'dt': MIN_TIME, 'v': p['vf']}, {'dt': p['dt']-MIN_TIME, 'v': p['vf']}]

class LinRamp(object):
    required_parameters = [
        ('vf', ([-VLIM, VLIM], [(0, 'V'), (-3, 'mV')], 6)),
        ('dt', ([1e-6, 50], [(0, 's'), (-3, 'ms'), (-6, 'us')], 2)), 
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
        return [{'dt': p['dt'], 'v': p['vf']}]

class SLinRamp(object):
    required_parameters = [
        ('vi', ([-VLIM, VLIM], [(0, 'V'), (-3, 'mV')], 6)),
        ('vf', ([-VLIM, VLIM], [(0, 'V'), (-3, 'mV')], 6)),
        ('dt', ([1e-6, 50], [(0, 's'), (-3, 'ms'), (-6, 'us')], 2)), 
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
        return [{'dt': MIN_TIME, 'v': p['vi']}, {'dt': p['dt']-MIN_TIME, 'v': p['vf']}]

class ExpRamp(object):
    required_parameters = [
        ('vf', ([-VLIM, VLIM], [(0, 'V')], 6)),
        ('dt', ([1e-6, 50], [(0, 's'), (-3, 'ms'), (-6, 'us')], 2)), 
        ('tau', ([-1e2, 1e2], [(0, 's'), (-3, 'ms'), (-6, 'us'), (-9, 'ns')], 2)),
        ('pts', ([1, 50], [(0, 'na')], 0)),
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
        return [{'dt': round_dt(s['tf']-s['ti']), 'v': round_dv(s['vf'])} for s in seq]

class SExpRamp(object):
    required_parameters = [
        ('vi', ([-VLIM, VLIM], [(0, 'V')], 6)),
        ('vf', ([-VLIM, VLIM], [(0, 'V')], 6)),
        ('dt', ([1e-6, 50], [(0, 's'), (-3, 'ms'), (-6, 'us')], 2)), 
        ('tau', ([-1e2, 1e2], [(0, 's'), (-3, 'ms'), (-6, 'us')], 2)),
        ('pts', ([1, 50], [(0, 'na')], 0)),
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
        return [{'dt': MIN_TIME, 'v': p['vi']}] + [{'dt': s['tf']-s['ti'], 'v': s['vf']} for s in seq]


class SCurveRamp(object):
    required_parameters = [
        ('vi', ([-VLIM, VLIM], [(0, 'V')], 6)),
        ('vf', ([-VLIM, VLIM], [(0, 'V')], 6)),
        ('dt', ([1e-6, 50], [(0, 's'), (-3, 'ms'), (-6, 'us')], 2)), 
        ('steep', ([-10, 10], [(0, 'na')], 2)),
        ('pts', ([1, 20], [(0, 'na')], 0)),
        ]
    def __init__(self, p=None):
        self.p = p
        if p is not None:
            self.v = scurve_ramp(p)
    
    def to_lin(self):
        """
        to list of linear ramps [{dt, dv}]
        """
        p = self.p
        seq = scurve_ramp(p, ret_seq=True)
        return [{'dt': MIN_TIME, 'v': p['vi']}] + [{'dt': s['tf']-s['ti'], 'v': s['vf']} for s in seq]


class RampMaker(object):
    available_ramps = {
        's': SRamp,
        'lin': LinRamp,
        'slin': SLinRamp,
        'exp': ExpRamp,
        'sexp': SExpRamp,
        'scurve': SCurveRamp
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
            if 'vi' not in sequence[i]:
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
