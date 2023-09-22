"""
Classes and functions for generating sequences for the RF synthesizer

To do:
    * Design functions for maintaining phase on frequency switching
    * Finish implementing SyncPoints
"""
from __future__ import annotations
from copy import copy, deepcopy
import numpy as np
from scipy.interpolate import interp1d
from typing import List, Optional
from json import dumps, JSONEncoder
import jsonpickle
from dataclasses import dataclass

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

MAX_FREQUENCY = 307.2E6 # Hertz
MAX_LENGTH = 16384
MIN_DURATION = 1/153.6E6
MAX_DURATION = 2**48*MIN_DURATION # seconds
N_DIGITAL = 7

class SequenceState():
    """
    Records the state of a synthesizer channel at any point in the sequence. Used by :func:`compile_sequence` and the :meth:`RFBlock.compile`.
    """
    def __init__(self, amplitude: float = 0, phase: float = 0, frequency: float = 1E6, transition:Transition = None, time: float = 0, triggers: int = 0, syncpoints: List[SyncPoint] = [], digital_out: List[bool] = [False]*7) -> None:
        """
        Args:
            amplitude (float): The amplitude of the channel. Defaults to 0.
            phase (float): The phase of the channel. Defaults to 0.
            frequency (float): The frequency of the channel. Defaults to 1E6.
            transition (:class:`Transition`): The selected transition, as set by :class:`SetTransition`. Defaults to None.
            time (float): The time since the start or the last trigger. Defaults to 0.
            triggers (int): The number of triggers required so far. Defaults to 0.
            syncpoints (list of str): The ordered list of :class:`SyncPoint` so far. Defaults to :code:`[]`.
            digital_out (list of bool): The state of the digital outputs. Defaults to :code:`[False]*7`.
        """
        self.amplitude = amplitude
        self.phase = phase
        self.frequency = frequency
        self.transition = transition
        self.time = time
        self.triggers = triggers
        self.syncpoints = syncpoints
        self.digital_out = digital_out

@dataclass
class RFBlock():
    """
    A base class for elements of a sequence for a synthesizer channel.

    Parameters:
        atomic (bool): Whether the block is handled directly by the compiler (True) or returns a sequence of blocks which need to be compiled (False). Defaults to False.
    """

    atomic = False

    def compile(self, state: Optional[SequenceState] = None) -> RFBlock | List[RFBlock]:
        """
        compile(self)

        Compiles the block into a list of basic :class:`RFBlock` that can be sent to the synthesizer.

        Args:
            state (:class:`SequenceState`, optional): The state of the channel when the block is to be called. Defaults to None, which can be used for testing :code:`compile` functions of :class:`RFBlock` objects that do not depend on channel state.

        Returns:
            (RFBlock | List[RFBlock]): The compiled :class:`RFBlock`.
        """
        return self

    def __repr__(self) -> str:
        raise NotImplementedError("Please implement me in subclasses.")

class RFPulse(RFBlock):
    """
    A base class for RF pulses.
    """
    @staticmethod
    def center(center: bool, sequence: List[RFBlock], duration: float):
        """
        center(center, sequence, duration):

        Helper function for centering a pulse by adjusting the duration of the surrounding :class:`Timestamp`. Should be included in the :meth:`RFBlock.compile` methods of subclasses as

        .. code-block:: python

            sequence = generate_some_stuff()
            return RFPulse.center(self.center, sequence, self.duration)

        Args:
            center (bool): Whether to center the sequence by adjusting the time of the surrounding :class:`Timestamp`.
            sequence (List[RFBlock]): The sequence.
            duration (float): The duration of the sequence in seconds.

        Returns:
            (list of :class:`RFBlock`): The sequence, centered if :code:`center`.
        """
        if center:
            return [AdjustPrevDuration(-duration/2)] + sequence + [AdjustNextDuration(-duration/2)]
        else:
            return sequence

    @property
    def area(self) -> float:
        """
        area(self)

        Returns the area of the pulse, relative to a rectangular pulse of the same duration and peak amplitude.

        Returns:
            (float): The area of the pulse, relative to a rectangular pulse of the same duration and peak amplitude
        """
        raise NotImplementedError("Please implement me in each subclass!")

    def compile(self, state:SequenceState = None) -> RFBlock | List[RFBlock]:
        raise NotImplementedError("Please implement me in each subclass!")

def validate_parameters(duration=None, amplitude: Optional[float] = None, phase: Optional[float] = None, frequency: Optional[float] = None) -> None:
    """
    validate_parameters(duration=None, amplitude=None, phase=None, frequency=None)

    Checks that commonly used parameters are within acceptable ranges.

    Args:
        duration (float, optional): Duration in seconds. Checks that it's non-negative. Defaults to None.
        amplitude (float, optional): Amplitude relative to full scale. Checks that it's between zero and one. Defaults to None.
        phase (float, optional): Phase in radians. Checks that it's a real number. Defaults to None.
        frequency (float, optional): Frequency in Hertz. Checks that it's between zero and :code:`MAX_FREQUENCY`. Defaults to None.

    Raises:
        ValueError: If any of the parameters are not None and outside their valid range.
    """
    if duration is not None and (duration < 0 or duration > MAX_DURATION):
        raise ValueError("Duration {} must be between zero and {}.".format(duration, MAX_DURATION))
    if amplitude is not None and (amplitude < 0 or amplitude > 1):
        raise ValueError("Amplitude {} must be between zero and one.".format(amplitude))
    if phase is not None and not np.isreal(phase):
        raise ValueError("Phase {} must be a real number.".format(phase))
    if frequency is not None and (frequency < 0 or frequency > MAX_FREQUENCY):
        raise ValueError("Frequency {} must be between 0 and {}.".format(frequency, MAX_FREQUENCY))

class Timestamp(RFBlock):
    """
    A single timestamp, at which the amplitude, phase, and frequency of the tone can be set for a specified duration.
    """

    atomic = True

    def __init__(self, duration: float, amplitude: Optional[float] = None, phase: Optional[float] = None, frequency: Optional[float] = None, wait_for_trigger: Optional[bool] = False, digital_out: Optional[dict] = {}, absolute_phase: Optional[bool] = False) -> None:
        """
        Args:
            duration (float): The duration of the timestamp. If the duration is zero, the parameters override ommited parameters in the next Timestamp.
            amplitude (float, optional): The amplitude of the tone relative to full scale. Defaults to None, in which case the previous amplitude is maintained.
            phase (float, optional): The phase of the tone in radians. Defaults to None, in which case the previous phase is maintained.
            frequency (float, optional): The frequency of the tone in Hertz. Defaults to None, in which case the previous frequency is maintained.
            wait_for_trigger (bool, optional): Whether to wait for a trigger to start the timestamp. Defaults to False.
            digital_out ({int: bool}, optional): A dictionary with keys (integers between 0 and 6) corresponding to the indices of digital outputs to set and boolean values corresponding to the desired state of the output. If a key is not present, the corresponding output is unchanged. Only used for the first channel. Defaults to {}.
            absolute_phase (bool, optional): If true, sets the phase to :code:`phase` radians at the beginning of the timestamp. Otherwise offsets the phase to :code:`phase` radians relative to a reference clock. If True, :code:`phase` must not be None. Defaults to False.
        """
        self.duration = duration
        self.amplitude = amplitude
        self.phase = phase
        self.frequency = frequency
        self.wait_for_trigger = wait_for_trigger
        self.digital_out = digital_out
        self.absolute_phase = absolute_phase
        self.phase_update = 0

    def __repr__(self) -> str:
        val = "Timestamp({}".format(self.duration)
        if self.amplitude is not None:
            val += ", amplitude={}".format(self.amplitude)
        if self.phase is not None:
            val += ", phase={}".format(self.phase)
        if self.frequency is not None:
            val += ", frequency={}".format(self.frequency)
        if self.wait_for_trigger:
            val += ", wait_for_trigger={}".format(self.wait_for_trigger)
        if len(self.digital_out) > 0:
            val += ", digital_out={}".format(self.digital_out)
        return val + ")"

    def compile(self, state: Optional[SequenceState] = None) -> Timestamp:
        validate_parameters(self.duration, self.amplitude, self.phase, self.frequency)
        if self.absolute_phase and self.phase is None:
            raise ValueError("Phase cannot be None if absolute_phase is True")
        state.time += self.duration
        if self.amplitude is not None:
            state.amplitude = self.amplitude
        if self.absolute_phase:
            self.phase_update = 1
            state.phase = self.phase
        elif self.phase is not None and self.phase != state.phase:
            self.phase_update = 2
            state.phase = self.phase
        if self.frequency is not None:
            state.frequency = self.frequency
        if self.wait_for_trigger:
            state.triggers += 1
            state.time = 0
        state.digital_out = copy(state.digital_out)
        for c, v in self.digital_out.items():
            if not isinstance(v, bool):
                raise ValueError("Digital output {} must be boolean but is {}.".format(c, v))
            if c < 0 or c >= N_DIGITAL:
                raise ValueError("Digital output {} is out of range.".format(c))
            state.digital_out[c] = v
        
        # Turn on the RF switch if the amplitude is non-zero
        state.digital_out[0] = state.amplitude > 0

        return super().compile(state)

class Wait(Timestamp):
    """
    Waits for a fixed duration.
    """
    def __init__(self, duration: float, wait_for_trigger: bool = False) -> None:
        """
        Args:
            duration (float): The duration to wait in seconds.
            wait_for_trigger (bool): Whether to wait for a trigger. Defaults to False.
        """
        super().__init__(duration, wait_for_trigger=wait_for_trigger)

class SyncPoint(RFBlock):
    """
    Allows different channels to be synchronized. If SyncPoints with the same name appear in different channels, an appropriate sequence of :class:`Wait` blocks are inserted into the channels for which it would occur earlier such that all channels reach the SyncPoint at the same time.

    Throws an error upon compilation if multiple SyncPoints with the same name occur in one channel's sequence or in an order such that they cannot be applied.
    """

    atomic = True

    def __init__(self, name: str) -> None:
        """
        Args:
            name: An identifier for the synchronization point.
        """
        self.name = name
    
    def __repr__(self) -> str:
        return "SyncPoint('{}')".format(self.name)
    
    def compile(self, state: SequenceState) -> SyncPoint:
        state.syncpoints.append(self.name)
        return super().compile(state)

class AdjustPrevDuration(RFBlock):
    """
    Adjusts the duration of the previous :class:`Timestamp`. Throws an error on compilation if the previous :class:`RFBlock` is not a :class:`Timestamp` or the adjustment would result in negative duration.
    """

    atomic = True

    def __init__(self, duration: float) -> None:
        """
        Args:
            duration (float): The duration in seconds by which to increment the duration of the previous timestamp.
        """
        self.duration = duration

    def __repr__(self) -> str:
        return "AdjustPrevDuration({})".format(self.duration)

    def compile(self, state: SequenceState) -> AdjustPrevDuration:
        state.time += self.duration
        return super().compile(state)

class AdjustNextDuration(RFBlock):
    """
    Adjusts the duration of the next :class:`Timestamp`. Throws an error on compilation if the next :class:`RFBlock` is not a :class:`Timestamp` or the adjustment would result in negative duration.
    """

    atomic = True

    def __init__(self, duration: float) -> None:
        """
        Args:
            duration (float): The duration in seconds by which to increment the duration of the next timestamp.
        """
        self.duration = duration

    def __repr__(self) -> str:
        return "AdjustNextDuration({})".format(self.duration)

    def compile(self, state: SequenceState) -> AdjustNextDuration:
        state.time += self.duration
        return super().compile(state)

class RectangularPulse(RFPulse):
    """
    Generates a `rectangular pulse <https://en.wikipedia.org/wiki/List_of_window_functions#Rectangular_window>`_.
    """
    def __init__(self, duration: float, amplitude: float, phase: Optional[float] = None, frequency: Optional[float] = None, centered: bool = False) -> None:
        """
        Refer to :func:`Pulse` for descriptions of the arguments.
        """
        self.duration = duration
        self.amplitude = amplitude
        self.phase = phase
        self.frequency = frequency
        self.centered = centered

    @property
    def area(self) -> float:
        return 1

    def compile(self, state: Optional[SequenceState] = None) -> List[RFBlock]:
        validate_parameters(self.duration, self.amplitude, self.phase, self.frequency)
        sequence = [
            Timestamp(self.duration, self.amplitude, self.phase, self.frequency),
            Timestamp(0, 0)
        ]
        return RFPulse.center(self.centered, sequence, self.duration)

    def __repr__(self) -> str:
        val = "RectangularPulse({}, {}".format(self.duration, self.amplitude)
        if self.phase is not None:
            val += ", phase={}".format(self.phase)
        if self.frequency is not None:
            val += ", frequency={}".format(self.frequency)
        if self.centered:
            val += ", centered=True"
        return val + ")"

class BlackmanPulse(RFPulse):
    """
    Generates a pulse with an `Blackman window <https://en.wikipedia.org/wiki/List_of_window_functions#Blackman_window>`_.
    """
    def __init__(self, duration: float, amplitude: float, phase: Optional[float] = None, frequency: Optional[float] = None, centered: Optional[float] = False, steps: int = 20, exact: bool = False) -> None:
        """
        Refer to :func:`Pulse` for descriptions of the arguments.

        Keyword Args:
            steps (int, optional): The number of steps to approximate the pulse. Should be at least 7. Defaults to 20.
            exact (bool, optional): Whether to use exact parameters for the window, as described `on Wikipedia <https://en.wikipedia.org/wiki/List_of_window_functions#Blackman_window>`_. Defaults to False.
        """
        self.duration = duration
        self.amplitude = amplitude
        self.phase = phase
        self.frequency = frequency
        self.centered = centered
        self.steps = steps
        self.exact = exact

    def __repr__(self) -> str:
        val = "BlackmanPulse({}, {}".format(self.duration, self.amplitude)
        if self.phase is not None:
            val += ", phase={}".format(self.phase)
        if self.frequency is not None:
            val += ", frequency={}".format(self.frequency)
        if self.centered:
            val += ", centered=True"
        if self.steps is not None:
            val += ", steps={}".format(self.steps)
        return val + ", exact={})".format(self.exact)

    @property
    def area(self) -> float:
        self.compile()
        step = self.duration/self.steps
        return step * sum(self.amplitudes)  / (self.amplitude * self.duration)

    def compile(self, state: Optional[SequenceState] = None) -> List[RFBlock]:
        validate_parameters(self.duration, self.amplitude, self.phase, self.frequency)
        if self.steps < 7 or int(self.steps) != self.steps:
            raise ValueError("Steps (currently {}) must be an integer >= 7.".format(self.steps))
        if self.exact:
            a = [7938.0/18608, 9240.0/18608, 1430.0/18608]
        else:
            a = [0.42, 0.5, 0.08]
        step = self.duration/self.steps
        N = self.steps - 1
        n = np.linspace(0, N, self.steps, endpoint=True)
        self.amplitudes = self.amplitude * (a[0] - a[1] * np.cos(2*np.pi*n/N) + a[2] * np.cos(4*np.pi*n/N))
        timestamps = [Timestamp(step, min(1, max(amp, 0))) for amp in self.amplitudes]
        timestamps[0].phase = self.phase
        timestamps[0].frequency = self.frequency
        return RFPulse.center(self.centered, timestamps + [Timestamp(0,0)], self.duration)
        

class GaussianPulse(RFPulse):
    """
    Generates a pulse with an `approximate confined Gaussian window <https://en.wikipedia.org/wiki/List_of_window_functions#Approximate_confined_Gaussian_window>`_. See also `here <http://dx.doi.org/10.1016/j.sigpro.2014.03.033>`_ for more details.
    """
    def __init__(self, duration: float, amplitude: float, phase: Optional[float] = None, frequency: Optional[float] = None, centered: bool = False, steps: int = 26, sigt: float = 0.11) -> None:
        """
        Refer to :func:`Pulse` for descriptions of the arguments.

        Keyword Args:
            steps (int, optional): The number of steps to approximate the pulse. Should be at least 16. Defaults to 26.
            sigt (float, optional): The RMS time width of the pulse relative to duration. Approximates a cosine window for :math:`\\sigma_{t} \\approx 0.18` and approaches the time-frequency uncertainty limit for :math:`\\sigma_{t} \\leq 0.13`. Throws an error if not between 0.08 and 0.20. Defaults to 0.11.
        """
        self.duration = duration
        self.amplitude = amplitude
        self.phase = phase
        self.frequency = frequency
        self.centered = centered
        self.sigt = sigt
        self.steps = steps

    @property
    def area(self) -> float:
        self.compile()
        step = self.duration/self.steps
        return step * sum(self.amplitudes) / (self.amplitude * self.duration)

    def compile(self, state: Optional[SequenceState] = None) -> List[RFBlock]:
        validate_parameters(self.duration, self.amplitude, self.phase, self.frequency)
        if self.sigt < 0.08 or self.sigt > 0.2:
            raise ValueError("sigt (currently {}) must be between 0.08 and 0.20.".format(self.sigt))
        if self.steps < 16 or int(self.steps) != self.steps:
            raise ValueError("Steps (currently {}) must be an integer >= 16.".format(self.steps))

        step = self.duration/self.steps
        N = self.steps - 1
        L = self.steps
        n = np.linspace(0, N, self.steps, endpoint=True)

        def G(x):
            return np.exp(-((x - N/2.0)/(2* L * self.sigt))**2)

        self.amplitudes = self.amplitude * (G(n) - (G(-0.5) * (G(n + L) + G(n - L)))/(G(L - 0.5) + G(-L - 0.5)))
        timestamps = [Timestamp(step, min(1, max(amp, 0))) for amp in self.amplitudes]
        timestamps[0].phase = self.phase
        timestamps[0].frequency = self.frequency
        return RFPulse.center(self.centered, timestamps + [Timestamp(0,0)], self.duration)

    def __repr__(self) -> str:
        val = "GaussianPulse({}, {}".format(self.duration, self.amplitude)
        if self.phase is not None:
            val += ", phase={}".format(self.phase)
        if self.frequency is not None:
            val += ", frequency={}".format(self.frequency)
        if self.centered:
            val += ", centered=True"
        if self.steps is not None:
            val += ", steps={}".format(self.steps)
        if self.sigt is not None:
            val += ", sigt={}".format(self.sigt)
        return val + ")"

class FrequencyRamp(RFBlock):
    """
    Linearly ramps the frequency of the RF tone while maintaining constant amplitude and phase.
    """
    def __init__(self, duration: float, amplitude: Optional[float] = None, phase: Optional[float] = None, start_frequency: Optional[float] = None, end_frequency: Optional[float] = None, steps: int = 20):
        """
        Args:
            duration (float): The duration of the ramp in seconds.
            amplitude (float, optional): The amplitude of the tone relative to full scale. Defaults to None.
            phase (float, optional): The phase of the tone in radians. Defaults to None, in which case the previous phase setting is maintained.
            start_frequency (float, optional): The initial frequency in Hertz. Defaults to None, in which case the previous frequency setting is used.
            end_frequency (float, optional): The final frequency in Hertz. Defaults to None, in which case :code:`start_frequency` is used.
            steps (int, optional): The number of frequency steps to include in the ramp. Defaults to 20.
        """
        self.duration = duration
        self.amplitude = amplitude
        self.phase = phase
        self.start_frequency = start_frequency
        self.end_frequency = end_frequency
        self.steps = steps

    def compile(self, state: SequenceState) -> List[RFBlock]:
        validate_parameters(self.duration, self.amplitude, self.phase, self.start_frequency)
        validate_parameters(frequency=self.end_frequency)
        if self.steps < 2 or self.steps != int(self.steps):
            raise ValueError("The number of steps, {}, must be an integer >= 2")
        if self.start_frequency is None:
            self.start_frequency = state.frequency
        if self.end_frequency is None:
            self.end_frequency = self.start_frequency
        step = self.duration/self.steps
        freqs = np.linspace(self.start_frequency, self.end_frequency, self.steps)
        timestamps = [Timestamp(step, frequency=freq) for freq in freqs]
        timestamps[0].phase = self.phase
        timestamps[0].amplitude = self.amplitude
        return timestamps

    def __repr__(self) -> str:
        val = "FrequencyRamp({}".format(self.duration)
        if self.amplitude is not None:
            val += ", amplitude={}".format(self.amplitude)
        if self.phase is not None:
            val += ", phase={}".format(self.phase)
        if self.start_frequency is not None:
            val += ", start_frequency={}".format(self.start_frequency)
        if self.end_frequency is not None:
            val += ", end_frequency={}".format(self.end_frequency)
        val += ", steps={})".format(self.steps)
        return val


class AmplitudeRamp(RFBlock):
    """
    Linearly ramps the amplitude of the RF tone while maintaining constant frequency and phase.
    """
    def __init__(self, duration: float, start_amplitude: Optional[float] = None, end_amplitude: Optional[float] = None, phase: Optional[float] = None, frequency: Optional[float] = None, steps: int = 20):
        """
        Args:
            duration (float): The duration of the ramp in seconds.
            start_amplitude (float, optional): The initial amplitude, relative to full scale. Defaults to None, in which case the amplitude of the previous :class:`RFBlock` is used.
            end_amplitude (float, optional): The final amplitude, relative to full scale. Defaults to None, in which case :code:`start_amplitude` is used.
            phase (float, optional): The phase of the tone in radians. Defaults to None, in which case the previous phase setting is maintained.
            frequency (float, optional): The frequency of the tone in Hertz. Defaults to None, in which case the previous frequency setting is maintained.
            steps (int, optional): The number of amplitude steps to include in the ramp. Must be at least 2. Defaults to 20.
        """
        self.duration = duration
        self.start_amplitude = start_amplitude
        self.end_amplitude = end_amplitude
        self.phase = phase
        self.frequency = frequency
        self.steps = steps

    def compile(self, state:SequenceState) -> List[RFBlock]:
        validate_parameters(self.duration, self.start_amplitude, self.phase, self.frequency)
        validate_parameters(amplitude=self.end_amplitude)
        if self.steps < 2 or self.steps != int(self.steps):
            raise ValueError("The number of steps, {}, must be an integer >= 2")
        if self.start_amplitude is None:
            self.start_amplitude = state.amplitude
        if self.end_amplitude is None:
            self.end_amplitude = self.start_amplitude
        step = self.duration/self.steps
        amps = np.linspace(self.start_amplitude, self.end_amplitude, self.steps)
        timestamps = [Timestamp(step, amplitude=amp) for amp in amps]
        timestamps[0].phase = self.phase
        timestamps[0].frequency = self.frequency
        return timestamps

    def __repr__(self) -> str:
        val = "AmplitudeRamp({}".format(self.duration)
        if self.start_amplitude is not None:
            val += ", start_amplitude={}".format(self.start_amplitude)
        if self.end_amplitude is not None:
            val += ", end_amplitude={}".format(self.end_amplitude)
        if self.phase is not None:
            val += ", phase={}".format(self.phase)
        if self.frequency is not None:
            val += ", frequency={}".format(self.frequency)
        val += ", steps={})".format(self.steps)
        return val
        
class PhaseRamp(RFBlock):
    """
    Linearly ramps the amplitude of the RF tone while maintaining constant frequency and phase.
    """
    def __init__(self, duration: float, amplitude: Optional[float] = None, start_phase: Optional[float] = None, end_phase: Optional[float] = None, frequency: Optional[float] = None, steps: int = 20):
        """
        Args:
            duration (float): The duration of the ramp in seconds.
            amplitude (float, optional): The amplitude of the tone relative to full scale. Defaults to None, in which case the previous ammplitude setting is maintained.
            start_phase (float, optional): The initial phase in radians. Defaults to None, in which case the phase of the previous :class:`RFBlock` is used.
            end_phase (float, optional): The final phase in radians. Defaults to None, in which case :code:`start_phase` is used.
            frequency (float, optional): The frequency of the tone in Hertz. Defaults to None, in which case the previous frequency setting is maintained.
            steps (int, optional): The number of amplitude steps to include in the ramp. Must be at least 2. Defaults to 20.
        """
        self.duration = duration
        self.amplitude = amplitude
        self.start_phase = start_phase
        self.end_phase = end_phase
        self.frequency = frequency
        self.steps = steps

    def compile(self, state:SequenceState) -> List[RFBlock]:
        validate_parameters(self.duration, self.amplitude, self.start_phase, self.frequency)
        validate_parameters(phase=self.end_phase)
        if self.steps < 2 or self.steps != int(self.steps):
            raise ValueError("The number of steps, {}, must be an integer >= 2")
        if self.start_phase is None:
            self.start_phase = state.phase
        if self.end_phase is None:
            self.end_phase = self.start_phase
        step = self.duration/self.steps
        phis = np.linspace(self.start_phase, self.end_phase, self.steps)
        timestamps = [Timestamp(step, phase=phi) for phi in phis]
        timestamps[0].amplitude = self.amplitude
        timestamps[0].frequency = self.frequency
        return timestamps

    def __repr__(self) -> str:
        val = "PhaseRamp({}".format(self.duration)
        if self.amplitude is not None:
            val += ", amplitude={}".format(self.amplitude)
        if self.start_phase is not None:
            val += ", start_phase={}".format(self.start_phase)
        if self.end_phase is not None:
            val += ", end_phase={}".format(self.end_phase)
        if self.frequency is not None:
            val += ", frequency={}".format(self.frequency)
        val += ", steps={})".format(self.steps)
        return val

class Transition():
    """
    Describes the calibrated frequency and Rabi frequencies for a transition. Used in :class:`SetTransition` to set parameters for :func:`AreaPulse`.
    """
    def __init__(self, frequency: float, amplitudes, Rabi_frequencies=None, default_amplitude:Optional[float] = None, frequency_offset: float = 0) -> None:
        """
        Args:
            frequency (float): The frequency of the transition in Hertz.
            amplitudes (dict or list of float): A list of amplitudes (relative to full scale) for which the Rabi frequencies are calibrated. Linearly interpolates and extrapolates relative to specified amplitudes. Can also take a dictionary with amplitude keys and Rabi frequency values, in which case Rabi_frequencies is ignored.
            Rabi_frequencies (list of float, optional): A list of Rabi frequencies (in Hertz) corresponding to :code:`amplitudes`. Must be the same length as :code:`amplitudes` if lists are used. Defaults to None.
            default_amplitude (float, optional): The default amplitude for pulses on the transition. Defaults to None, in which case the first element of amplitudes is used.
            frequency_offset (float, optional): The frequency (in Hertz) of the tone that is mixed with the synthesizer output. The actual output frequency of the synthesizer is :code:`frequency - frequency_offset`. Defaults to 0.
        """
        if isinstance(amplitudes, dict):
            amplitudes_list=[]
            Rabi_frequencies=[]
            for k, v in amplitudes.items():
                amplitudes_list.append(k)
                Rabi_frequencies.append(v)
            amplitudes = amplitudes_list
        if len(amplitudes) == 0 or len(Rabi_frequencies) != len(amplitudes):
            raise ValueError("amplitudes and Rabi_frequencies must be non-empty arrays of the same length.")
        for a in amplitudes:
            if a <= 0 or a >1:
                raise ValueError("All amplitudes must be > 0 and <= 1; {} isn't.".format(a))
        for f in Rabi_frequencies:
            if f <= 0:
                raise ValueError("All Rabi frequencies must be positive; {} isn't.".format(f))
        if default_amplitude is not None and (default_amplitude <= 0 or default_amplitude > 1):
            raise ValueError("Default amplitude {} must be > 0 and <= 1".format(default_amplitude))
        if frequency - frequency_offset < 0 or frequency - frequency_offset > MAX_FREQUENCY:
            raise ValueError("The output frequency (frequency {} - frequency_offset {}) must be between 0 and {} but is {}".format(frequency, frequency_offset, MAX_FREQUENCY, frequency - frequency_offset))
        self.frequency = frequency
        self.amplitudes = amplitudes
        self.Rabi_frequencies = Rabi_frequencies
        if default_amplitude is None:
            default_amplitude = amplitudes[0]
        self.default_amplitude = default_amplitude
        
        self.frequency_offset = frequency_offset
        if len(self.amplitudes) > 1:
            itp = interp1d(self.amplitudes, self.Rabi_frequencies, copy=False, fill_value="extrapolate")
            self.default_Rabi_frequency = itp(self.default_amplitude)
        else:
            self.default_Rabi_frequency = Rabi_frequencies[0]

    def __repr__(self) -> str:
        return "Transition({}, {}, {}, default_amplitude={}, frequency_offset={})".format(self.frequency, self.amplitudes, self.Rabi_frequencies, self.default_amplitude, self.frequency_offset)

    def Rabi_frequency(self, amplitude: Optional[float] = None) -> float:
        """
        Rabi_frequency(self, amplitude=None)

        Computes the Rabi frequency corresponding to :code:`amplitude` using interpolation or extrapolation from the values provided by :code:`amplitudes` and :code:`Rabi_frequencies`.

        Args:
            amplitude (float, optional): The amplitude for which to compute the Rabi frequency. Defaults to None, in which case :code:`default_amplitude` is used.

        Returns:
            float: The Rabi frequency, in Hertz, associated with :code:`amplitude`.
        """
        if amplitude is None:
            amplitude = self.default_amplitude
        if amplitude <= 0 or amplitude > 1:
            raise ValueError("Amplitude {} must be > 0 and <= 1".format(amplitude))
        if len(self.amplitudes) > 1:
            itp = interp1d(self.amplitudes, self.Rabi_frequencies, copy=False, fill_value="extrapolate")
            return itp(amplitude)
        else:
            return self.default_Rabi_frequency

class SetTransition(RFBlock):
    """
    Sets the transition to be used for subsequent :meth:`AreaPulse` commands.
    """

    atomic = True

    def __init__(self, transition: Transition) -> None:
        """
        Args:
            transition (Transition): The transition to use for the following :meth:`AreaPulse` commands.
        """
        self.transition = transition

    def __repr__(self) -> str:
        return "SetTransition({})".format(self.transition)

    def compile(self, state: SequenceState) -> RFBlock:
        state.transition = self.transition
        state.frequency = self.transition.frequency - self.transition.frequency_offset
        return super().compile(state)

def todB(amplitude_lin):
    """
    todB(amplitude_lin)

    Converts an amplitude ratio from linear to decibels per :math:`A_{dB} = 20 \\log_{10}(A)`.

    Args:
        amplitude_lin (float): An amplitude ratio.

    Returns:
        float: The amplitude ratio in decibels.
    """
    return 20.0*np.log10(amplitude_lin)

def fromdB(amplitude_dB):
    """
    fromdB(amplitude_dB)

    Converts an amplitude ratio from decibels to linear per :math:`A = 10^{A_{dB}/20}`.

    Args:
        amplitude_lin (float): An amplitude ratio in decibels.

    Returns:
        float: The amplitude ratio.
    """
    return 10**(amplitude_dB/20)

def Pulse(duration: float, amplitude: float, phase: Optional[float] = None, frequency: Optional[float] = None, centered: bool = False, window: type[RFPulse] = RectangularPulse, **kwargs) -> RFPulse:
    """
    Pulse(duration, amplitude, phase=None, frequency=None, centered=False, window=RectangularPulse, **kwargs)

    Low level function for generating an RF pulse. Provides a unified constructor for all subclasses of :class:`RFPulse`. See also :func:`AreaPulse` for a higher level interface to pulses on a specified :class:`Transition`.

    Args:
        duration (float): The duration of the pulse in seconds.
        amplitude (float): The peak amplitude of the pulse, relative to full scale.
        phase (float, optional): The phase of the pulse in radians. Defaults to None, in which case the previous phase setting is maintained.
        frequency (float, optional): The frequency of the pulse in Hertz. Defaults to None, in which case the previous frequency setting is maintained.
        centered (bool, optional): Whether to reduce the duration of the preceding and following :class:`Wait` commands :code:`duration/2`. Will throw an error during compilation if the :class:`Wait` commands are too short or the pulse is not adjacent to at least one :class:`Wait` command. If there is only one neighboring :class:`Wait` command, its duration is reduced by :code:`duration/2`. Defaults to False.
        window (RFPulse, optional): The shape of the pulse. Defaults to RectangularPulse.
        **kwargs: Additional keyword arguments, which are passed to :code:`window`'s :code:`__init__` method

    Returns:
        RFPulse: An :class:`RFPulse` with the specified parameters
    """
    return window(duration, amplitude, phase, frequency, centered, **kwargs)

class AreaPulse(RFPulse):
    """
    Class for generating an RF pulse on a specified :class:`Transition`, which must be set by a :class:`SetTransition` command before the first :func:`AreaPulse`. The pulse timing is calculated to provide the specified pulse :code:`area`. See also :func:`Pulse` for a low level function for generating pulses with manually specified frequency, amplitude, and duration.
    """
    
    def __init__(self, pulse_area: float, amplitude: Optional[float] = None, phase: Optional[float] = None, frequency: Optional[float] = None, centered: bool = False, window: type[RFPulse] = RectangularPulse, **kwargs) -> None:
        """
        Args:
            pulse_area (float): The pulse area in radians.
            amplitude (float, optional): The peak amplitude of the pulse, relative to full scale. Defaults to None, in which case the default amplitude for the specified :class:`Transition` is used.
            phase (float, optional): The phase of the pulse in radians. Defaults to None, in which case the previous phase setting is maintained.
            centered (bool, optional): Whether to reduce the duration of the preceding and following :class:`Wait` commands :code:`duration/2`. Will throw an error during compilation if the :class:`Wait` commands are too short or the pulse is not adjacent to at least one :class:`Wait` command. If there is only one neighboring :class:`Wait` command, its duration is reduced by :code:`duration/2`. Defaults to False.
            window (RFPulse, optional): The shape of the pulse. Defaults to RectangularPulse.
            **kwargs: Additional keyword arguments, which are passed to window's :code:`__init__` method
        """
        self.pulse_area = pulse_area
        self.amplitude = amplitude
        self.phase = phase
        self.frequency = frequency
        self.centered = centered
        self.window = window
        self.kwargs = kwargs

    def compile(self, state: SequenceState) -> List[RFPulse]:
        if issubclass(self.window, AreaPulse):
            return self.window(self.pulse_area, self.amplitude, self.phase, self.centered, **self.kwargs).compile(state)
        transition = state.transition
        if self.frequency is None:
            self.frequency = transition.frequency
        if self.amplitude is None:
            self.amplitude = transition.default_amplitude
        if self.amplitude <= 0 or self.amplitude > 1:
            raise ValueError("Amplitude {} must be > 0 and <= 1".format(self.amplitude))
        if self.pulse_area < 0:
            raise ValueError("Pulse area {} must be non-negative".format(self.pulse_area))
        validate_parameters(phase=self.phase)
        if self.pulse_area == 0:
            return [Wait(0)]
        Rabi_frequency = transition.Rabi_frequency(self.amplitude)
        rect_pulse_duration = self.pulse_area/(2*np.pi*Rabi_frequency)
        pulse = Pulse(1, self.amplitude, self.phase, self.frequency - transition.frequency_offset, self.centered, self.window, **self.kwargs)
        pulse.duration = rect_pulse_duration/pulse.area
        return [pulse]

    def __repr__(self) -> str:
        val = "AreaPulse({}".format(self.pulse_area)
        if self.amplitude is not None:
            val += ", amplitude={}".format(self.amplitude)
        if self.phase is not None:
            val += ", phase={}".format(self.phase)
        val += ", centered={}, window={}".format(self.centered, self.window)
        if len(self.kwargs) > 0:
            val += ", {}".format(self.kwargs)
        val += ")"
        return val

def PiPulse(amplitude: Optional[float] = None, phase: Optional[float] = None, frequency: Optional[float] = None, centered: bool = False, window: type[RFPulse] = RectangularPulse, **kwargs) -> AreaPulse:
    """
    PiPulse(amplitude=None, phase=None, centered=False, window=RectangularPulse, **kwargs)

    A wrapper for :func:`AreaPulse` with pulse area set to pi. Refer to :func:`AreaPulse` for full documentation.
    """
    return AreaPulse(np.pi, amplitude=amplitude, phase=phase, frequency=frequency, centered=centered, window=window, **kwargs)

def PiOver2Pulse(amplitude: Optional[float] = None, phase: Optional[float] = None, frequency: Optional[float] = None, centered: bool = False, window: type[RFPulse] = RectangularPulse, **kwargs) -> AreaPulse:
    """
    PiOver2Pulse(amplitude=None, phase=None, centered=False, window=RectangularPulse, **kwargs)

    A wrapper for :func:`AreaPulse` with pulse area set to pi/2. Refer to :func:`AreaPulse` for full documentation.
    """
    return AreaPulse(np.pi/2, amplitude=amplitude, phase=phase, frequency=frequency, centered=centered, window=window, **kwargs)

class BB1(AreaPulse):
    """
    Generates a `BB1 <https://doi.org/10.1006/jmra.1994.1159>`_ robust composite pulse.
    """

    def compile(self, state: SequenceState) -> List[RFPulse]:
        if self.phase is None:
            self.phase = state.phase
        phi1 = np.arccos(-self.pulse_area / (2*np.pi))
        phi2 = 3*phi1
        pulses =  [
            PiPulse(self.amplitude, self.phase + phi1, False, self.window, **self.kwargs),
            AreaPulse(2*np.pi, self.amplitude, self.phase + phi2, False, self.window, **self.kwargs),
            PiPulse(self.amplitude, self.phase + phi1, False, self.window, **self.kwargs),
            AreaPulse(self.pulse_area, self.amplitude, self.phase, False, self.window, **self.kwargs)
        ]
        self.duration = 0
        for p in pulses: 
            self.duration += deepcopy(p).compile(deepcopy(state))[0].duration
        return AreaPulse.center(self.centered, pulses, self.duration)

    def __repr__(self) -> str:
        val = "BB1({}".format(self.pulse_area)
        if self.amplitude is not None:
            val += ", amplitude={}".format(self.amplitude)
        if self.phase is not None:
            val += ", phase={}".format(self.phase)
        val += ", centered={}, window={}".format(self.centered, self.window)
        if len(self.kwargs) > 0:
            val += ", {}".format(self.kwargs)
        val += ")"
        return val
    
class CORPSE(AreaPulse):
    """
    Generates a `CORPSE <https://doi.org/10.1103/PhysRevA.67.042308>`_ robust composite pulse.
    """

    def compile(self, state: SequenceState) -> List[RFPulse]:
        if self.phase is None:
            self.phase = state.phase
        theta = self.pulse_area
        theta1 = 2*np.pi + theta/2.0 - np.arcsin(np.sin(theta/2.0)/2.0)
        theta2 = 2*np.pi - 2*np.arcsin(np.sin(theta/2.0)/2.0)
        theta3 = theta/2.0 - np.arcsin(np.sin(theta/2.0)/2.0)
        pulses =  [
            AreaPulse(theta1, self.amplitude, self.phase, self.centered, self.window, **self.kwargs),
            AreaPulse(theta2, self.amplitude, self.phase + np.pi, self.centered, self.window, **self.kwargs),
            AreaPulse(theta3, self.amplitude, self.phase, self.centered, self.window, **self.kwargs)
        ]
        self.duration = 0
        for p in pulses: 
            self.duration += deepcopy(p).compile(deepcopy(state))[0].duration
        return AreaPulse.center(self.centered, pulses, self.duration)

    def __repr__(self) -> str:
        val = "CORPSE({}".format(self.pulse_area)
        if self.amplitude is not None:
            val += ", amplitude={}".format(self.amplitude)
        if self.phase is not None:
            val += ", phase={}".format(self.phase)
        val += ", centered={}, window={}".format(self.centered, self.window)
        if len(self.kwargs) > 0:
            val += ", {}".format(self.kwargs)
        val += ")"
        return val

def SpinEcho(duration: float, pulse: Optional[RFPulse] = None) -> List[RFBlock]:
    """
    SpinEcho(duration, pulse=None)

    Returns a list of pulses and :class:`Wait` commands implementing a spin echo decoupling sequence consisting of a `duration/2` :class:`Wait`, a pi pulse about the :code:`x` axis and another :code:`duration/2` :class:`Wait`.

    Args:
        duration (float): The duration of the decoupling sequence in seconds.
        pulse (RFPulse, optional): The pulse to use for the pi pulses in the decoupling sequence. Should normally be generated by :func:`PiPulse` or be a subclass of :class:`RFPulse`. The phase of the pulse is overridden in the sequence. Defaults to None, in which case a :class:`RectangularPulse` with the default amplitude and frequency for the selected :class:`Transition` is used.

    Returns:
        list of :class:`RFBlock`: Returns a list of pulses and :class:`Wait` commands implementing a spin echo decoupling sequence.
    """
    if pulse is None:
        pulse = PiPulse(phase=0, centered=True)
    elif isinstance(pulse, type) and issubclass(pulse, RFPulse):
        pulse = PiPulse(window=pulse, centered=True)
    else:
        pulse.phase = 0
    return [Wait(duration/2), pulse, Wait(duration/2)]

def XY8(duration: float, pulse: RFPulse = None) -> List[RFBlock]:
    """
    XY8(duration, pulse=None)

    Returns a list of pulses and :class:`Wait` commands implementing an XY8 decoupling sequence. Refer to `this review <https://doi.org/10.1098/rsta.2011.0355>`_ for information about the XY8 pulse sequence.

    Args:
        duration (float): The duration of the decoupling sequence in seconds.
        pulse (RFPulse, optional): The pulse to use for the pi pulses in the decoupling sequence. Should normally be generated by :func:`PiPulse` or be a subclass of :class:`RFPulse`. The phase of the pulses are overridden in the sequence. Defaults to None, in which case a :class:`RectangularPulse` with the default amplitude and frequency for the selected :class:`Transition` is used.

    Returns:
        list of :class:`RFBlock`: Returns a list of pulses and :class:`Wait` commands implementing an XY8 decoupling sequence.
    """
    if pulse is None:
        pulse = PiPulse(phase=0, centered=True)
    elif isinstance(pulse, type) and issubclass(pulse, RFPulse):
        pulse = PiPulse(window=pulse, centered=True)
    def phased_pulse(phase):
        new_pulse = copy(pulse)
        new_pulse.phase = phase
        return new_pulse
    phases = [0, np.pi/2, 0, np.pi/2, np.pi/2, 0, np.pi/2, 0] # XYXYYXYX
    return [Wait(duration/16)] + [f(phi) for phi in phases for f in (phased_pulse, lambda x: Wait(duration/8))][:-1] + [Wait(duration/16)]

def XY16(duration: float, pulse:Optional[RFPulse] = None) -> List[RFBlock]:
    """
    XY16(duration, pulse=None)

    Returns a list of pulses and :class:`Wait` commands implementing an XY16 decoupling sequence. Refer to `this review <https://doi.org/10.1098/rsta.2011.0355>`_ for information about the XY8 pulse sequence.

    Args:
        duration (float): The duration of the decoupling sequence in seconds.
        pulse (RFPulse, optional): The pulse to use for the pi pulses in the decoupling sequence. Should normally be generated by :func:`PiPulse` or be a subclass of :class:`RFPulse`. The phase of the pulses are overridden in the sequence. Defaults to None, in which case a :class:`RectangularPulse` with the default amplitude and frequency for the selected :class:`Transition` is used.

    Returns:
        list of :class:`RFBlock`: Returns a list of pulses and :class:`Wait` commands implementing an XY16 decoupling sequence.
    """
    if pulse is None:
        pulse = PiPulse(phase=0, centered=True)
    elif isinstance(pulse, type) and issubclass(pulse, RFPulse):
        pulse = PiPulse(window=pulse, centered=True)
    def phased_pulse(phase):
        new_pulse = copy(pulse)
        new_pulse.phase = phase
        return new_pulse
    phases = [0, np.pi/2, 0, np.pi/2, np.pi/2, 0, np.pi/2, 0, np.pi, 3*np.pi/2, np.pi, 3*np.pi/2, 3*np.pi/2, np.pi, 3*np.pi/2, np.pi] # XYXYYXYX-X-Y-X-Y-Y-X-Y-X
    return [Wait(duration/32)] + [f(phi) for phi in phases for f in (phased_pulse, lambda x: Wait(duration/16))][:-1] + [Wait(duration/32)]

class KDD:
    """
    KDD(duration, pulse=None)

    Returns a list of pulses and :class:`Wait` commands implementing a KDD decoupling sequence. Refer to `this review <https://doi.org/10.1098/rsta.2011.0355>`_ and `this paper <https://journals.aps.org/prl/pdf/10.1103/PhysRevLett.106.240501>`_ for information about the KDD pulse sequence.

    Args:
        duration (float): The duration of the decoupling sequence in seconds.
        pulse (RFPulse, optional): The pulse to use for the pi pulses in the decoupling sequence. Should normally be generated by :func:`PiPulse` or be a subclass of :class:`RFPulse`. The phase of the pulses are overridden in the sequence. Defaults to None, in which case a :class:`RectangularPulse` with the default amplitude and frequency for the selected :class:`Transition` is used.

    Returns:
        list of :class:`RFBlock`: Returns a list of pulses and :class:`Wait` commands implementing a KDD decoupling sequence.
    """

    def __init__(self, duration: float, pulse: Optional[RFPulse] = None) -> None:
        self.duration = duration
        self.pulse = pulse

    def __repr__(self) -> str:
        return f"KDD({self.duration.__repr__()}, {self.pulse.__repr__()})"

    def compile(self, state: SequenceState) -> List[RFBlock]:
        if self.pulse is None:
            self.pulse = PiPulse(phase=0, centered=True)
        elif isinstance(self.pulse, type) and issubclass(self.pulse, RFPulse):
            self.pulse = PiPulse(window=self.pulse, centered=True)

        def phased_pulse(phase):
            new_pulse = copy(self.pulse)
            new_pulse.phase = phase
            return new_pulse
        
        tau = self.duration/20.0
        def KDDphi(phi):
            return [Wait(tau/2.0),
                phased_pulse(np.pi/6 + phi),
                Wait(tau),
                phased_pulse(phi),
                Wait(tau),
                phased_pulse(np.pi/2 + phi),
                Wait(tau),
                phased_pulse(phi),
                Wait(tau),
                phased_pulse(np.pi/6 + phi),
                Wait(tau/2.0)]
            
        return KDDphi(0) + KDDphi(np.pi/2) + KDDphi(0) + KDDphi(np.pi/2)

def WAHUHA(duration: float, pulse: RFPulse = None):
    if pulse is None:
        pulse = PiOver2Pulse()
    def phased_pulse(phase, area):
        new_pulse = copy(pulse)
        new_pulse.phase = phase
        new_pulse.pulse_area = area
        new_pulse.centered = True
        return new_pulse

    sequence = [
        Wait(duration/8),
        phased_pulse(np.pi, np.pi/2),
        Wait(duration/4),
        phased_pulse(0, np.pi/2),
        Wait(duration/8),
        phased_pulse(0, np.pi),
        Wait(duration/8),
        phased_pulse(np.pi, np.pi/2),
        Wait(duration/4),
        phased_pulse(0, np.pi/2),
        Wait(duration/8)
    ]

    return sequence

def DROID60(duration: float, pulse: RFPulse = None):
    if pulse is None:
        pulse = PiOver2Pulse()
    def phased_pulse(phase, area):
        new_pulse = copy(pulse)
        new_pulse.phase = phase
        new_pulse.pulse_area = area
        new_pulse.centered = False
        return new_pulse
    
    def px():
        return phased_pulse(0, np.pi)
    def p2x():
        return phased_pulse(0, np.pi/2)
    def py():
        return phased_pulse(np.pi/2, np.pi)
    def p2y():
        return phased_pulse(np.pi/2, np.pi/2)
    def mpx():
        return phased_pulse(np.pi, np.pi)
    def mp2x():
        return phased_pulse(np.pi, np.pi/2)
    def mpy():
        return phased_pulse(3*np.pi/2, np.pi)
    def mp2y():
        return phased_pulse(3*np.pi/2, np.pi/2)
    def w():
        return Wait(duration/48)

    seq = [w(),px(),w(),p2x(),mp2y(),w(),mpx(),w(),mpx(),w(),px(),w(),p2x(),mp2y(),w(),mpx(),w(),mpx(),w(),px(),w(),p2x(),mp2y(),w(),mpx(),w(),mpx(),w(),mpy(),w(),mp2y(),p2x(),w(),py(),w(),py(),w(),mpy(),w(),mp2y(),p2x(),w(),py(),w(),py(),w(),mpy(),w(),mp2y(),p2x(),w(),py(),w(),py(),w(),mpy(),w(),p2x(),p2y(),w(),py(),w(),mpy(),w(),mpy(),w(),p2x(),p2y(),w(),py(),w(),mpy(),w(),mpy(),w(),p2x(),p2y(),w(),py(),w(),mpx(),w(),mpx(),w(),p2y(),p2x(),w(),px(),w(),mpx(),w(),mpx(),w(),p2y(),p2x(),w(),px(),w(),mpx(),w(),mpx(),w(),p2y(),p2x(),w(),px(),w(),mpy()]
    return seq

def Ramsey(duration: float, phase: float = 0, pulse: RFPulse = None, decoupling: List[RFPulse | Wait] = None) -> List[RFBlock]:
    """
    Ramsey(duration, phase, pulse=None, decoupling=None)

    Returns a list of pulses and :class:`Wait` commands implementing a Ramsey interferometry sequence, consisting of a pi/2 pulse with zero phase, a :class:`Wait` of length :code:`duration`, and a final pi/2 pulse with phase :code:`phase`. A decoupling sequence can optionally be inserted instead of the :class:`Wait`.

    Args:
        duration (float): The dark time (in seconds) for the Ramsey sequence.
        phase (float, optional): The phase of the final pulse. Defaults to 0.
        pulse (RFPulse, optional): The pulse to use for the pi/2 pulses in the Ramsey sequence. Should normally be generated by :func:`PiOver2Pulse` or be a subclass of :class:`RFPulse`. The phase of the pulses are overridden in the sequence. Defaults to None, in which case a :class:`RectangularPulse` with the default amplitude and frequency for the selected :class:`Transition` is used.
        decoupling (list of :class:`RFBlock`, optional): A decoupling sequence (generated by :func:`XY8`, for example) to insert during the dark time. The duration of :class:`Wait` commands is adjusted to make the total length equal to :code:`duration`. Must only contain :class:`RFPulse` and :class:`Wait` blocks. Defaults to None.
         
    Returns:
        list of :class:`RFBlock`: Returns a list of pulses and :class:`Wait` commands implementing a Ramsey sequence.
    """
    if decoupling == None:
        decoupling = [Wait(duration)]
    else:
        decoupling = deepcopy(decoupling)
        decoupling_duration = 0
        for b in decoupling:
            if isinstance(b, Wait):
                decoupling_duration += b.duration
            elif isinstance(b, RFPulse):
                b.centered = True
            else:
                raise TypeError("Only RFPulse and Wait are allowed in the decoupling sequence. {} was included.".format(b))
        for b in decoupling:
            if isinstance(b, Wait):
                b.duration *= duration/decoupling_duration
    if pulse is None:
        pulse = PiOver2Pulse()
    elif isinstance(pulse, type) and issubclass(pulse, RFPulse):
        pulse = PiPulse(window=pulse, centered=True)
    else:
        pulse.phase = 0
    end_pulse = copy(pulse)
    end_pulse.phase = phase
    return [pulse] + decoupling + [end_pulse]
        


def compile_sequence(sequence: List[RFBlock], output_json: bool = True) -> List[RFBlock] | str:
    """
    compile_sequence(sequence)

    Compilation steps:
        * Compiles instance of :class:`RFBlock` with :code:`compile` functions
        * Updates durations based on :class:`AdjustPrevDuration` and :class:`AdjustNextDuration`
        * Replaces :class:`SyncPoint` blocks with  :class:`Wait` blocks.
        * Converts timestamps from relative to absolute time
        * Computes durations of each section of the sequence
        * Outputs the sequence in a list of serializable dictionaries that can be sent to the synthesizer server.

    Args:
        sequence (dictionary of lists of :class:`RFBlock`): The sequence to compile. Keys should be channels, values should be list of :class:`RFBlock`.
        output_json (bool): Outputs a JSON-formatted string of timestamos that can be sent to :class:`synthesizer.synthesizer_server` if True, or a list of :class:`RFBlock` if False. Defaults to True.

    Returns
        ((List[RFBlock] | str), Dict[int : List[float]]): A tuple containing the compiled sequence and a list of lists the durations of the sequences for each channel
    """

    compiled = {}
    all_durations = {}

    sequence = deepcopy(sequence)
    for channel, stack in sequence.items():
        stack.reverse()
        state = SequenceState()
        compiled_channel = []
        while len(stack) > 0:
            head = stack.pop()
            if isinstance(head, List):
                head.reverse()
                stack += head
                continue
            if hasattr(head, "atomic") and head.atomic:
                block = head.compile(state)
                if len(compiled_channel) > 0 and isinstance(compiled_channel[-1], AdjustNextDuration) and not isinstance(block, Timestamp):
                    raise TypeError("{} must be followed by a Timestamp, but is followed by {}".format(compiled_channel[-1], block))
                if isinstance(block, SyncPoint):
                    raise(NotImplementedError())
                elif isinstance(block, SetTransition):
                    pass
                elif isinstance(block, AdjustPrevDuration):
                    if len(compiled_channel) == 0:
                        pass
                    elif not isinstance(compiled_channel[-1], Timestamp):
                        raise TypeError("{} must follow a Timestamp, but follows {}".format(block, compiled_channel[-1]))
                    elif -block.duration > compiled_channel[-1].duration:
                        raise ValueError("{} would make the duration of {} negative".format(block, compiled_channel[-1]))
                    else:
                        compiled_channel[-1].duration += block.duration
                elif isinstance(block, Timestamp):
                    if len(compiled_channel) > 0 and isinstance(compiled_channel[-1], AdjustNextDuration):
                        adjust_next = compiled_channel.pop()
                        if -adjust_next.duration > block.duration:
                            raise ValueError("{} would make the duration of {} negative".format(adjust_next, block))
                        else:
                            block.duration += adjust_next.duration
                    if block.amplitude is None:
                        block.amplitude = state.amplitude
                    if block.phase is None:
                        block.phase = state.phase
                    if block.frequency is None:
                        block.frequency = state.frequency
                    if block.duration > 0:
                        compiled_channel.append(block)
                    elif block.wait_for_trigger:
                        if block.duration == 0:
                            block.duration = MIN_DURATION
                        compiled_channel.append(block)
                    elif block.duration == 0 and len(stack) > 0 and isinstance(stack[-1], Timestamp) and stack[-1].wait_for_trigger:
                        block.duration = MIN_DURATION
                        compiled_channel.append(block)
                    block.digital_out = state.digital_out
                elif isinstance(block, AdjustNextDuration):
                    compiled_channel.append(block)
                else:
                    raise TypeError("Cannot add a {} to the sequence".format(block))
            else:
                blocks = head.compile(state)
                blocks.reverse()
                stack.extend(blocks)
        durations = []
        duration = 0
        compiled_channel = [b for b in compiled_channel if isinstance(b, Timestamp)]
        for block in compiled_channel:
            if block.wait_for_trigger:
                durations.append(duration)
                duration = 0
            block.duration, duration = duration, block.duration + duration
            if duration > MAX_DURATION:
                raise ValueError("The duration {} s of channel {}'s sequence exceeds the maximum duration of {} s after {}".format(duration, channel, MAX_DURATION, block))
        durations.append(duration)
        if len(compiled_channel) > 0 and compiled_channel[-1].duration != duration:
            compiled_channel.append(Timestamp(duration, amplitude=state.amplitude, phase=state.phase,frequency=state.frequency, digital_out=state.digital_out))
        terminator = Timestamp(0, 0, 0, 0, digital_out=[False]*N_DIGITAL)
        terminator.phase_update = 0
        compiled_channel.append(terminator)
        if len(compiled_channel) > MAX_LENGTH:
            raise ValueError("The length {} of channel {}'s sequence exceeds the maximum length of {}".format(len(compiled_channel), channel, MAX_LENGTH))
        compiled[channel] = compiled_channel
        all_durations[channel] = durations
    if output_json:
        class RFBlockEncoder(JSONEncoder):
            def default(self, obj):
                if isinstance(obj, Timestamp):
                    return {
                        "timestamp": obj.duration,
                        "phase_update": obj.phase_update,
                        "phase": obj.phase,
                        "amplitude": obj.amplitude,
                        "frequency": obj.frequency,
                        "wait_for_trigger": obj.wait_for_trigger,
                        "digital_out": obj.digital_out
                    }
                if isinstance(obj, np.bool_):
                    return bool(obj)
                return JSONEncoder.default(self, obj)
        return dumps(compiled, cls=RFBlockEncoder), all_durations
    else:
        return compiled, all_durations
    
def plot_sequence(seq: List[RFBlock]):
    """
    plot_sequence(seq)

    Plots a sequence using Plotly.

    Args:
        seq ([RFBlock]): The sequence to plot
    """
    compiled, durations = compile_sequence(seq, output_json=False)

    fig = make_subplots(rows=3+N_DIGITAL, cols=1, shared_xaxes=True, vertical_spacing=0.015, row_heights=[0.25, 0.25, 0.25] + [0.2/N_DIGITAL]*N_DIGITAL)

    plot_data = {}
    for channel, seq_channel in compiled.items():
        times = []
        ampls = []
        phases = []
        freqs = []
        digital = [[] for i in range(N_DIGITAL)]
        i = 0
        for block in seq_channel[:-1]:
            if block.wait_for_trigger:
                plot_data[str((channel, i))] = {"time": times, "amplitude": ampls, "phase": phases, "frequency": freqs, "digital": digital}
                times = []
                ampls = []
                phases = []
                freqs = []
                digital = [[] for i in range(N_DIGITAL)]
                i += 1
            times.append(block.duration)
            ampls.append(block.amplitude)
            phases.append(block.phase)
            freqs.append(block.frequency)
            for j, b in enumerate(block.digital_out):
                digital[j].append(1 if b else 0)
        plot_data[str((channel, i))] = {"time": times, "amplitude": ampls, "phase": phases, "frequency": freqs, "digital":digital}

    color_i = 0
    colors = px.colors.qualitative.Plotly
    for k, pd in plot_data.items():
        fig.add_trace(go.Scatter(x=pd["time"], y=pd["amplitude"], line_shape="hv", name="{}".format(k), fill='tozeroy', legendgroup = k, line_color=colors[color_i], mode="lines"), row=1, col=1)
        fig.add_trace(go.Scatter(x=pd["time"], y=pd["phase"], line_shape="hv", name="Phase {}".format(k), fill='tozeroy', legendgroup = k, line_color=colors[color_i], showlegend=False, mode="lines"), row=2, col=1)
        fig.add_trace(go.Scatter(x=pd["time"], y=pd["frequency"], line_shape="hv", name="Frequency {}".format(k), legendgroup = k, line_color=colors[color_i], showlegend=False, mode="lines"), row=3, col=1)
        if k[1] == '0':
            for i in range(N_DIGITAL):
                fig.add_trace(go.Scatter(x=pd["time"], y=pd["digital"][i], line_shape="hv", name="D{} {}".format(i, k), fill='tozeroy', legendgroup = k, line_color=colors[color_i], showlegend=False, mode="lines"), row=4+i, col=1)
        color_i += 1

    fig.update_xaxes(title_text="Time (s)", row=3+N_DIGITAL, col=1, rangemode="tozero", side="bottom")
    fig.update_yaxes(title_text="Frequency (Hz)", row=3, col=1)
    fig.update_yaxes(title_text="Amplitude", row=1, col=1, range=[0,1])
    fig.update_yaxes(title_text="Phase (rad)", row=2, col=1)
    for i in range(N_DIGITAL):
        fig.update_yaxes(title_text="D{}".format(i), row=4+i, col=1, range=[0,1], showticklabels=False)
    fig.update_layout(legend={'traceorder':'grouped'})

    fig.show()

    return (compiled, durations, fig)

def send_seq(seq):
    if isinstance(seq, List):
        # for s in seq:
        #     compile_sequence(s)
        return [jsonpickle.dumps(s, keys=True) for s in seq]
    else:
        # compile_sequence(s)
        return jsonpickle.dumps(seq, keys=True)
    