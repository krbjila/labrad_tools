"""
Classes and functions for generating sequences for the RF synthesizer

To do:
    * Design functions for maintaining phase on frequency switching
    * Finish implementing all functions
    * Develop low-level compiler that converts basic RFBlocks into synthesizer commands
    * Develop a graphical tool for visualizing RF sequences
    * Implement a conductor parameter for compiling RF sequences, exporting their durations as variables that can be used in sequencer, and programming the synthesizer
"""

import numpy as np

class RFBlock():
    """
    A base class for elements of a sequence for a synthesizer channel.
    """
    def compile(self, state=None):
        """
        compile(self)

        Compiles the block into a list of basic :class:`RFBlock` that can be sent to the synthesizer.

        Args:
            state (dict): The :code:`phase`, :code:`amplitude`, :code:`frequency`, and :class:`Transition` of the channel, as of the end of the previous block. Not used by default.

        Returns:
            (list of :class:`RFBlock`): The compiled :class:`RFBlock`.
        """
        return [self]

    def __repr__(self) -> str:
        raise ValueError("Please implement me in subclasses.")

class RFPulse(RFBlock):
    """
    An base class for RF pulses.
    """
    @staticmethod
    def center(center, sequence, duration):
        """
        center(center, sequence, duration):

        Helper function for centering a pulse by adjusting the duration of the surrounding :class:`Timestamp`. Should be included in the :meth:`RFBlock.compile` methods of subclasses as

        .. code-block:: python

            sequence = generate_some_stuff()
            return RFPulse.center(self.center, sequence, self.duration)

        Args:
            center (bool): Whether to center the sequence by adjusting the time of the surrounding :class:`Timestamp`.
            sequence (list of :class:`RFBlock`): The sequence.
            duration (float): The duration of the sequence in seconds.

        Returns:
            (list of :class:`RFBlock`): The sequence, centered if :code:`center`.
        """
        if center:
            return [AdjustPrevDuration(-duration/2)] + sequence + [AdjustNextDuration(-duration/2)]
        else:
            return sequence

    @property
    def area(self):
        """
        area(self)

        Returns the area of the pulse, relative to a rectangular pulse of the same duration and peak amplitude.
        """
        raise NotImplementedError("Please implement me in each subclass!")

    def compile(self, state=None):
        raise("Please implement me in each subclass!")

class Timestamp(RFBlock):
    """
    A single timestamp, at which the amplitude, phase, and frequency of the tone can be set for a specified duration.
    """
    def __init__(self, duration, amplitude=None, phase=None, frequency=None):
        """
        Args:
            duration (float): The duration of the timestamp. If the duration is zero, the parameters override ommited parameters in the next Timestamp.
            amplitude (float, optional): The amplitude of the tone relative to full scale. Defaults to None, in which case the previous amplitude is maintained.
            phase (float, optional): The phase of the tone in radians. Defaults to None, in which case the previous phase is maintained.
            frequency (float, optional): The frequency of the tone in Hertz. Defaults to None, in which case the previous frequency is maintained.
        """
        self.duration = duration
        self.amplitude = amplitude
        self.phase = phase
        self.frequency = frequency

    def __repr__(self) -> str:
        val = "Timestamp({}".format(self.duration)
        if self.amplitude is not None:
            val += ", amplitude={}".format(self.amplitude)
        if self.phase is not None:
            val += ", phase={}".format(self.phase)
        if self.frequency is not None:
            val += ", frequency={}".format(self.frequency)
        return val + ")"

class Wait(Timestamp):
    """
    Waits for a fixed duration.
    """
    def __init__(self, duration):
        """
        Args:
            duration (float): The duration to wait in seconds.
        """
        super().__init__(duration)

class WaitForTrigger(RFBlock):
    """
    Waits for the synthesizer to receive a software or hardware trigger.
    """
    def __init__(self):
        pass

    def __repr__(self) -> str:
        return "WaitForTrigger()"

class SyncPoint(RFBlock):
    """
    Allows different channels to be synchronized. If SyncPoints with the same name appear in different channels, an appropriate sequence of :class:`WaitForTrigger` and :class:`Wait` blocks are inserted into the channels for which it would occur earlier such that all channels reach the SyncPoint at the same time.

    Throws an error upon compilation if multiple SyncPoints with the same name occur in one channel's sequence or in an order such that they cannot be applied.
    """
    def __init__(self, name):
        """
        Args:
            name: An identifier for the synchronization point.
        """
        self.name = name
    
    def __repr__(self) -> str:
        return "SyncPoint({})".format(self.name)

class AdjustPrevDuration(RFBlock):
    """
    Adjusts the duration of the previous :class:`Timestamp`. Throws an error on compilation if the previous :class:`RFBlock` is not a :class:`Timestamp` or the adjustment would result in negative duration.
    """
    def __init__(self, duration):
        """
        Args:
            duration (float): The duration in seconds by which to increment the duration of the previous timestamp.
        """
        self.duration = duration

    def __repr__(self) -> str:
        return "AdjustPrevDuration({})".format(self.duration)

class AdjustNextDuration(RFBlock):
    """
    Adjusts the duration of the next :class:`Timestamp`. Throws an error on compilation if the next :class:`RFBlock` is not a :class:`Timestamp` or the adjustment would result in negative duration.
    """
    def __init__(self, duration):
        """
        Args:
            duration (float): The duration in seconds by which to increment the duration of the next timestamp.
        """
        self.duration = duration

    def __repr__(self) -> str:
        return "AdjustNextDuration({})".format(self.duration)

class RectangularPulse(RFPulse):
    """
    Generates a `rectangular pulse <https://en.wikipedia.org/wiki/List_of_window_functions#Rectangular_window>`_.
    """
    def __init__(self, duration, amplitude, phase=None, frequency=None, centered=False):
        """
        Refer to :func:`Pulse` for descriptions of the arguments.
        """
        self.duration = duration
        self.amplitude = amplitude
        self.phase = phase
        self.frequency = frequency
        self.centered = centered

    def area(self):
        return 1

    def compile(self, state=None):
        sequence = [
            Timestamp(self.duration, self.amplitude, self.phase, self.frequency),
            Timestamp(0, 0)
        ]
        return RFPulse.center(self.center, sequence, self.duration)

class BlackmanPulse(RFPulse):
    """
    Generates a pulse with an `Blackman window <https://en.wikipedia.org/wiki/List_of_window_functions#Blackman_window>`_.
    """
    def __init__(self, duration, amplitude, phase=None, frequency=None, centered=False, steps=20, exact=False):
        """
        Refer to :func:`Pulse` for descriptions of the arguments.

        Keyword Args:
            steps (int, optional): The number of steps to approximate the pulse. Should be at least 7. Defaults to 20.
            exact (bool, optional): Whether to use exact parameters for the window, as described `here <https://en.wikipedia.org/wiki/List_of_window_functions#Blackman_window>`_.
        """
        if duration <= 0:
            raise ValueError("The duration {} must be positive.".format(duration))
        self.duration = duration
        self.amplitude = amplitude
        self.phase = phase
        self.frequency = frequency
        self.centered = centered
        if steps < 7 or int(steps) != steps:
            raise ValueError("Steps (currently {}) must be an integer >= 7.".format(steps))
        self.steps = steps
        self.exact = exact

    def area(self):
        self.compile()
        return self.step * sum(self.amplitudes)  / (self.amplitude * self.duration)

    def compile(self, state=None):
        if self.exact:
            a = [7938.0/18608, 9240.0/18608, 1430.0/18608]
        else:
            a = [0.42, 0.5, 0.08]
        self.step = self.duration/self.steps
        N = self.steps - 1
        n = np.linspace(0, N, self.steps, endpoint=True)
        self.amplitudes = self.amplitude * (a[0] - a[1] * np.cos(2*np.pi*n/N) + a[2] * np.cos(4*np.pi*n/N))
        timestamps = [Timestamp(self.step, amp) for amp in self.amplitudes]
        timestamps[0].phase = self.phase
        timestamps[0].frequency = self.frequency
        return RFPulse.center(self.centered, timestamps + [Timestamp(0,0)], self.duration)
        

class GaussianPulse(RFPulse):
    """
    Generates a pulse with an `approximate confined Gaussian window <https://en.wikipedia.org/wiki/List_of_window_functions#Approximate_confined_Gaussian_window>`_. See also `here <http://dx.doi.org/10.1016/j.sigpro.2014.03.033>`_ for more details.
    """
    def __init__(self, duration, amplitude, phase=None, frequency=None, centered=False, steps=26, sigt=0.11):
        """
        Refer to :func:`Pulse` for descriptions of the arguments.

        Keyword Args:
            steps (int, optional): The number of steps to approximate the pulse. Should be at least 16. Defaults to 26.
            sigt (float, optional): The RMS time width of the pulse relative to duration. Approximates a cosine window for :math:`\\sigma_{t} \\approx 0.18` and approaches the time-frequency uncertainty limit for :math:`\\sigma_{t} \\leq 0.13`. Throws an error if not between 0.08 and 0.20. Defaults to 0.11.
        """
        if duration <= 0:
            raise ValueError("The duration {} must be positive.".format(duration))
        self.duration = duration
        self.amplitude = amplitude
        self.phase = phase
        self.frequency = frequency
        self.centered = centered
        if sigt < 0.08 or sigt > 0.2:
            raise ValueError("sigt (currently {}) must be between 0.08 and 0.20.".format(sigt))
        self.sigt = sigt
        if steps < 16 or int(steps) != steps:
            raise ValueError("Steps (currently {}) must be an integer >= 16.".format(steps))
        self.steps = steps

    def area(self):
        self.compile()
        return self.step * sum(self.amplitudes) / (self.amplitude * self.duration)

    def compile(self, state=None):
        self.step = self.duration/self.steps
        N = self.steps - 1
        L = self.steps
        n = np.linspace(0, N, self.steps, endpoint=True)

        def G(x):
            return np.exp(-((x - N/2.0)/(2* L * self.sigt))**2)

        self.amplitudes = self.amplitude * (G(n) - (G(-0.5) * (G(n + L) + G(n - L)))/(G(L - 0.5) + G(-L - 0.5)))
        timestamps = [Timestamp(self.step, amp) for amp in self.amplitudes]
        timestamps[0].phase = self.phase
        timestamps[0].frequency = self.frequency
        return RFPulse.center(self.centered, timestamps + [Timestamp(0,0)], self.duration)

class FrequencyRamp(RFBlock):
    """
    Linearly ramps the frequency of the RF tone while maintaining constant amplitude and phase.
    """
    def __init__(self, duration, amplitude=None, phase=None, start_frequency=None, end_frequency=None, steps=20):
        """
        Args:
            duration (float): The duration of the ramp in seconds.
            amplitude (float, optional): The amplitude of the tone relative to full scale. Defaults to None.
            phase (float, optional): The phase of the tone in radians. Defaults to None, in which case the previous phase setting is maintained.
            start_frequency (float, optional): The initial frequency in Hertz. Defaults to None, in which case the previous frequency setting is used.
            end_frequency (float, optional): The final frequency in Hertz. Defaults to None, in which case :code:`start_frequency` is used.
            steps (int, optional): The number of frequency steps to include in the ramp. Defaults to 20.
        """
        raise NotImplementedError()

    def compile(self, state):
        raise NotImplementedError()

class AmplitudeRamp(RFBlock):
    """
    Linearly ramps the amplitude of the RF tone while maintaining constant frequency and phase.
    """
    def __init__(self, duration, start_amplitude=None, end_amplitude=None, phase=None, frequency=None, steps=20):
        """
        Args:
            duration (float): The duration of the ramp in seconds.
            start_amplitude (float, optional): The initial amplitude, relative to full scale. Defaults to None, in which case the amplitude of the previous :class:`RFBlock` is used.
            end_amplitude (float, optional): The final amplitude, relative to full scale. Defaults to None, in which case :code:`start_amplitude` is used.
            phase (float, optional): The phase of the tone in radians. Defaults to None, in which case the previous phase setting is maintained.
            frequency (float, optional): The frequency of the tone in Hertz. Defaults to None, in which case the previous frequency setting is maintained.
            steps (int, optional): The number of amplitude steps to include in the ramp. Defaults to 20.

        """
        raise NotImplementedError()

    def compile(self, state):
        raise NotImplementedError()

class Transition():
    """
    Describes the calibrated frequency and Rabi frequencies for a transition. Used in :class:`SetTransition` to set parameters for :func:`AreaPulse`.
    """
    def __init__(self, frequency, amplitudes, Rabi_frequencies, default_amplitude=None, frequency_offset=0):
        """
        Args:
            frequency (float): The frequency of the transition in Hertz.
            amplitudes (list of float): A list of amplitudes (relative to full scale) for which the Rabi frequencies are calibrated. Linearly interpolates and extrapolates relative to specified amplitudes. 
            Rabi_frequencies (list of float): A list of Rabi frequencies (in Hertz) corresponding to :code:`amplitudes`. Must be the same length as :code:`amplitudes`.
            default_amplitude (float, optional): The default amplitude for pulses on the transition. Defaults to None, in which case the first element of amplitudes is used.
            synthesizer_offset (float, optional): The frequency (in Hertz) of the tone that is mixed with the synthesizer output. The actual output frequency of the synthesizer is :code:`frequency - synthesizer_offset`. Defaults to 0.
        """
        raise NotImplementedError()

class SetTransition(RFBlock):
    """
    Sets the transition to be used for subsequent :meth:`AreaPulse` commands.
    """
    def __init__(self, transition):
        """
        Args:
            transition (Transition): The transition to use for the following :meth:`AreaPulse` commands.
        """
        raise NotImplementedError

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

def Pulse(duration, amplitude, phase=None, frequency=None, centered=False, window=RectangularPulse, **kwargs):
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
        **kwargs: Additional keyword arguments, which are passed to window's :code:`__init__` method

    Returns:
        RFPulse: An :class:`RFPulse` with the specified parameters
    """
    return window(duration, amplitude, phase, frequency, centered, **kwargs)

class AreaPulse(RFPulse):
    """
    Class for generating an RF pulse on a specified :class:`Transition`, which must be set by a :class:`SetTransition` command before the first :func:`AreaPulse`. The pulse timing is calculated to provide the specified pulse :code:`area`. See also :func:`Pulse` for a low level function for generating pulses with manually specified frequency, amplitude, and duration.
    """
    
    def __init__(self, area, amplitude=None, phase=None, centered=False, window=RectangularPulse, **kwargs):
        """
        Args:
            area (float): The pulse area in radians.
            amplitude (float, optional): The peak amplitude of the pulse, relative to full scale. Defaults to None, in which case the default amplitude for the specified :class:`Transition` is used.
            phase (float, optional): The phase of the pulse in radians. Defaults to None, in which case the previous phase setting is maintained.
            centered (bool, optional): Whether to reduce the duration of the preceding and following :class:`Wait` commands :code:`duration/2`. Will throw an error during compilation if the :class:`Wait` commands are too short or the pulse is not adjacent to at least one :class:`Wait` command. If there is only one neighboring :class:`Wait` command, its duration is reduced by :code:`duration/2`. Defaults to False.
            window (RFPulse, optional): The shape of the pulse. Defaults to RectangularPulse.
            **kwargs: Additional keyword arguments, which are passed to window's :code:`__init__` method
        """
        pass

    def compile(self, state=None):
        pass

    def __repr__(self) -> str:
        pass

def PiPulse(amplitude=None, phase=None, center=False, window=RectangularPulse, **kwargs):
    """
    PiPulse(amplitude=None, phase=None, center=False, window=RectangularPulse, **kwargs)

    A wrapper for :func:`AreaPulse` with pulse area set to pi. Refer to :func:`AreaPulse` for full documentation.
    """
    return AreaPulse(np.pi, amplitude=None, phase=None, center=False, window=RectangularPulse, *kwargs)

def PiOver2Pulse(amplitude=None, phase=None, center=False, window=RectangularPulse, *kwargs):
    """
    PiOver2Pulse(amplitude=None, phase=None, center=False, window=RectangularPulse, **kwargs)

    A wrapper for :func:`AreaPulse` with pulse area set to pi/2. Refer to :func:`AreaPulse` for full documentation.
    """
    return AreaPulse(np.pi/2, amplitude=None, phase=None, center=False, window=RectangularPulse, **kwargs)

def SpinEcho(duration, pulse=None):
    """
    SpinEcho(duration, pulse=None)

    Returns a list of pulses and :class:`Wait` commands implementing a spin echo decoupling sequence consisting of a `duration/2` :class:`Wait`, a pi pulse about the :code:`x` axis and another :code:`duration/2` :class:`Wait`.

    Args:
        duration (float): The duration of the decoupling sequence in seconds.
        pulse (RFPulse, optional): The pulse to use for the pi pulses in the decoupling sequence. Should normally be generated by :func:`PiPulse`. The phase of the pulses are overridden in the sequence. Defaults to None, in which case a :class:`RectangularPulse` with the default amplitude and frequency for the selected :class:`Transition` is used.

    Returns:
        list of :class:`RFBlock`: Returns a list of pulses and :class:`Wait` commands implementing a spin echo decoupling sequence.
    """
    raise NotImplementedError()

def XY8(duration, pulse=None):
    """
    XY8(duration, pulse=None)

    Returns a list of pulses and :class:`Wait` commands implementing an XY8 decoupling sequence. Refer to `this review <https://doi.org/10.1098/rsta.2011.0355>`_ for information about the XY8 pulse sequence.

    Args:
        duration (float): The duration of the decoupling sequence in seconds.
        pulse (RFPulse, optional): The pulse to use for the pi pulses in the decoupling sequence. Should normally be generated by :func:`PiPulse`. The phase of the pulses are overridden in the sequence. Defaults to None, in which case a :class:`RectangularPulse` with the default amplitude and frequency for the selected :class:`Transition` is used.

    Returns:
        list of :class:`RFBlock`: Returns a list of pulses and :class:`Wait` commands implementing an XY8 decoupling sequence.
    """
    raise NotImplementedError()

def XY16(duration, pulse=None):
    """
    XY16(duration, pulse=None)

    Returns a list of pulses and :class:`Wait` commands implementing an XY16 decoupling sequence. Refer to `this review <https://doi.org/10.1098/rsta.2011.0355>`_ for information about the XY8 pulse sequence.

    Args:
        duration (float): The duration of the decoupling sequence in seconds.
        pulse (RFPulse, optional): The pulse to use for the pi pulses in the decoupling sequence. Should normally be generated by :func:`PiPulse`. The phase of the pulses are overridden in the sequence. Defaults to None, in which case a :class:`RectangularPulse` with the default amplitude and frequency for the selected :class:`Transition` is used.

    Returns:
        list of :class:`RFBlock`: Returns a list of pulses and :class:`Wait` commands implementing an XY16 decoupling sequence.
    """
    raise NotImplementedError()

def KDD(duration, pulse=None):
    """
    KDD(duration, pulse=None)

    Returns a list of pulses and :class:`Wait` commands implementing a KDD decoupling sequence. Refer to `this review <https://doi.org/10.1098/rsta.2011.0355>`_ and `this paper <https://journals.aps.org/prl/pdf/10.1103/PhysRevLett.106.240501>`_ for information about the KDD pulse sequence.

    Args:
        duration (float): The duration of the decoupling sequence in seconds.
        pulse (RFPulse, optional): The pulse to use for the pi pulses in the decoupling sequence. Should normally be generated by :func:`PiPulse`. The phase of the pulses are overridden in the sequence. Defaults to None, in which case a :class:`RectangularPulse` with the default amplitude and frequency for the selected :class:`Transition` is used.

    Returns:
        list of :class:`RFBlock`: Returns a list of pulses and :class:`Wait` commands implementing a KDD decoupling sequence.
    """
    raise NotImplementedError()

def Ramsey(duration, phase=0, pulse=None, decoupling=None):
    """
    Ramsey(duration, phase, pulse=None, decoupling=None)

    Returns a list of pulses and :class:`Wait` commands implementing a Ramsey interferometry sequence, consisting of a pi/2 pulse with zero phase, a :class:`Wait` of length :code:`duration`, and a final pi/2 pulse with phase :code:`phase`. A decoupling sequence can optionally be inserted instead of the :class:`Wait`.

    Args:
        duration (float): The dark time (in seconds) for the Ramsey sequence.
        phase (float, optional): The phase of the final pulse. Defaults to 0.
        pulse (RFPulse, optional): The pulse to use for the pi/2 pulses in the Ramsey sequence. Should normally be generated by :func:`PiOver2Pulse`. The phase of the pulses are overridden in the sequence. Defaults to None, in which case a :class:`RectangularPulse` with the default amplitude and frequency for the selected :class:`Transition` is used.
        decoupling (list of :class:`RFBlock`, optional): A decoupling sequence (generated by :func:`XY8`, for example) to insert during the dark time. The duration of :class:`Wait` commands is adjusted to make the total length equal to :code:`duration`. Defaults to None.

    Returns:
        list of :class:`RFBlock`: Returns a list of pulses and :class:`Wait` commands implementing a Ramsey sequence.
    """
    raise NotImplementedError()

def compile_sequence(sequence):
    """
    compile_sequence(sequence)

    Compilation steps:
        * Compiles instance of :class:`RFBlock` with :code:`compile` functions
        * Updates durations based on :class:`AdjustPrevDuration` and :class:`AdjustNextDuration`
        * Replaces :class:`SyncPoint` blocks with  :class:`Wait` and :class:`WaitForTrigger` blocks.
        * Converts timestamps from relative to absolute time
        * Computes durations of each section of the sequence
        * Outputs the sequence in a list of serializable dictionaries that can be sent to the synthesizer server.

    Args:
        sequence (list or list of lists of :class:`RFBlock`): The sequence to compile. If a list of lists is given, compiles multiple channels at once, handling :class:`SyncPoint` blocks. Otherwise, compiles a single channel's sequence, ignoring :class:`SyncPoint`.
    """
    pass