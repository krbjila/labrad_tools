from abc import abstractmethod, ABC
from math import pi

class RFBlock(ABC):
    @abstractmethod
    def compile(self):
        pass

class RFPulse(RFBlock):
    @property
    @abstractmethod
    def area(self):
        pass

class SetSingle(RFBlock):
    def __init__(self, duration, phase=None, amplitude=None, frequency=None):
        self.duration = duration
        self.phase = phase
        self.amplitude = amplitude
        self.frequency = frequency
    
    def compile(self):
        return [{
            "timestamp": self.duration,
            "phase_update": self.phase is not None,
            "phase": self.phase,
            "amplitude": self.amplitude,
            "frequency": self.frequency
        }]

class Wait(SetSingle):
    def __init__(self, duration):
        super().__init__(duration)

class WaitForTrigger(RFBlock):
    def compile(self):
        raise NotImplementedError()

class RFSequence(RFBlock):
    def __init__(self, data):
        self.data = data

    def compile(self):
        timestamps = []
        for s in self.data:
            timestamps += s.compile()
        return timestamps

class RectangularPulse(RFPulse):
    def __init__(self, duration, amplitude, phase=None, frequency=None, center=False):
        self.duration = duration
        self.amplitude = amplitude
        raise NotImplementedError()

    def area(self):
        return self.amplitude*self.duration

class BlackmanPulse(RFPulse):
    def __init__(self, duration, amplitude, phase=None, frequency=None, center=False, steps=20):
        raise NotImplementedError()

    def area(self):
        raise NotImplementedError()

class GaussianPulse(RFPulse):
    def __init__(self, duration, amplitude, phase=None, frequency=None, center=False, steps=20):
        raise NotImplementedError()

    def area(self):
        raise NotImplementedError()

class FrequencyRamp(RFSequence):
    def __init__(self, duration, amplitude=None, phase=None, start_frequency=None, end_frequency=None, steps=20):
        raise NotImplementedError()

class AmplitudeRamp(RFSequence):
    def __init__(self, duration, start_amplitude=None, end_amplitude=None, phase=None, frequency=None, steps=20):
        raise NotImplementedError()

class Transition():
    def __init__(self):
        raise NotImplementedError()

class setTransition():
    def __init__(self):
        raise NotImplementedError

def Pulse(duration, amplitude, phase=None, frequency=None, center=False, window=RectangularPulse, *kwargs):
    return window(duration, amplitude, phase, frequency, center, *kwargs)

def AreaPulse(area, amplitude=None, phase=None, center=False, window=RectangularPulse, *kwargs):
    raise NotImplementedError

def PiPulse(amplitude=None, phase=None, center=False, window=RectangularPulse, *kwargs):
    return AreaPulse(pi, amplitude=None, phase=None, center=False, window=RectangularPulse, *kwargs)

def PiOver2Pulse(amplitude=None, phase=None, center=False, window=RectangularPulse, *kwargs):
    return AreaPulse(pi/2, amplitude=None, phase=None, center=False, window=RectangularPulse, *kwargs)

def SpinEcho(duration, pulse=None):
    raise NotImplementedError()

def XY8(duration, pulse=None):
    raise NotImplementedError()

def XY16(duration, pulse=None):
    raise NotImplementedError()

def KDD(duration, pulse=None):
    # https://journals.aps.org/prl/pdf/10.1103/PhysRevLett.106.240501
    raise NotImplementedError()

def Ramsey(duration, phase, pulse=None, decoupling=None, *kwargs):
    raise NotImplementedError()