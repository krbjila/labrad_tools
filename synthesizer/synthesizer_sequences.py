"""
Classes and functions for generating sequences for the RF synthesizer

To do:
    * Design functions for maintaining phase on frequency switching
    * Fininsh implementing all functions
    * Develop low-level compiler that converts basic RFBlocks into synthesizer commands
    * Develop a graphical tool for visualizing RF sequences
    * Implement a conductor parameter for compiling RF sequences, exporting their durations as variables that can be used in sequencer, and programming the synthesizer
"""

from math import pi, log10

class RFBlock():
    """
    A base class for elements of a sequence for a synthesizer channel.
    """
    def compile(self):
        """
        compile(self)

        Compiles the block into a list of basic :class:`RFBlock` that can be sent to the synthesizer.

        Returns:
            (list of :class:`RFBlock`): The compiled :class:`RFBlock`.
        """
        return [self]

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
            (list of :class:`RFBlock`): The sequence, centered if `center`.
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

    def compile(self):
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

class SyncPoint(RFBlock):
    """
    Allows different channels to be synchronized. If SyncPoints with the same name appear in different channels, an appropriate sequence of :class:`WaitForTrigger` and :class:`Wait` blocks are inserted into the channels for which it would occur earlier such that all channels reach the SyncPoint at the same time.

    Throws an error upon compilation if SyncPoints with the same name occur in one channel's sequence or in an order such that they cannot be applied.
    """
    def __init__(self, name):
        """
        Args:
            name: An identifier for the synchronization point.
        """
        self.name = name

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

class RectangularPulse(RFPulse):
    """
    Generates a `rectangular pulse <https://en.wikipedia.org/wiki/List_of_window_functions#Rectangular_window>`_.
    """
    def __init__(self, duration, amplitude, phase=None, frequency=None, center=False):
        """
        Refer to :func:`Pulse` for descriptions of the arguments.
        """
        self.duration = duration
        self.amplitude = amplitude
        self.phase = phase
        self.frequency = frequency
        self.center = center

    def area(self):
        return 1

    def compile(self):
        sequence = [
            Timestamp(self.duration, self.amplitude, self.phase, self.frequency),
            Timestamp(0, 0)
        ]
        return RFPulse.center(self.center, sequence, self.duration)

class BlackmanPulse(RFPulse):
    """
    Generates a pulse with an `Blackman window <https://en.wikipedia.org/wiki/List_of_window_functions#Blackman_window>`_.
    """
    def __init__(self, duration, amplitude, phase=None, frequency=None, center=False, steps=20, exact=False):
        """
        Refer to :func:`Pulse` for descriptions of the arguments.

        Keyword Args:
            steps (int, optional): The number of steps to approximate the pulse. Defaults to 20.
            exact (bool, optional): Whether to use exact parameters for the window, as described `here <https://en.wikipedia.org/wiki/List_of_window_functions#Blackman_window>`_.
        """
        raise NotImplementedError()

    def area(self):
        raise NotImplementedError()

    def compile(self):
        raise NotImplementedError()

class GaussianPulse(RFPulse):
    """
    Generates a pulse with an `approximate confined Gaussian window <https://en.wikipedia.org/wiki/List_of_window_functions#Approximate_confined_Gaussian_window>`_.
    """
    def __init__(self, duration, amplitude, phase=None, frequency=None, center=False, steps=20):
        """
        Refer to :func:`Pulse` for descriptions of the arguments.

        Keyword Args:
            steps (int, optional): The number of steps to approximate the pulse. Defaults to 20.
        """
        raise NotImplementedError()

    def area(self):
        raise NotImplementedError()

    def compile(self):
        raise NotImplementedError()

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
            end_frequency (float, optional): The final frequency in Hertz. Defaults to None, in which case `start_frequency` is used.
            steps (int, optional): The number of frequency steps to include in the ramp. Defaults to 20.
        """
        raise NotImplementedError()

    def compile(self):
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
            end_amplitude (float, optional): The final amplitude, relative to full scale. Defaults to None, in which case `start_amplitude` is used.
            phase (float, optional): The phase of the tone in radians. Defaults to None, in which case the previous phase setting is maintained.
            frequency (float, optional): The frequency of the tone in Hertz. Defaults to None, in which case the previous frequency setting is maintained.
            steps (int, optional): The number of amplitude steps to include in the ramp. Defaults to 20.

        """
        raise NotImplementedError()

    def compile(self):
        raise NotImplementedError()

class Transition():
    """
    Describes the calibrated frequency and Rabi frequencies for a transition. Used in :class:`SetTransition` to set parameters for :func:`AreaPulse`.
    """
    def __init__(self, frequency, amplitudes, Rabi_frequencies, default_amplitude=None, frequency_offset=0):
        """
        Args:
            frequency (float): The frequency of the transition in Hertz.
            amplitudes (list of float): A list of amplitudes (relative to full scale) for which the Rabi frequencies are calibrated.
            Rabi_frequencies (list of float): A list of Rabi frequencies (in Hertz) corresponding to `amplitudes`. Must be the same length as `amplitudes`.
            default_amplitude (float, optional): The default amplitude for pulses on the transition. Defaults to None, in which case the first element of amplitudes is used.
            synthesizer_offset (float, optional): The frequency (in Hertz) of the tone that is mixed with the synthesizer output. The actual output frequency of the synthesizer is `frequency - synthesizer_offset`. Defaults to 0.
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
    return 20.0*log10(amplitude_lin)

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

def Pulse(duration, amplitude, phase=None, frequency=None, center=False, window=RectangularPulse, **kwargs):
    """
    Pulse(duration, amplitude, phase=None, frequency=None, center=False, window=RectangularPulse, **kwargs)

    Low level function for generating an RF pulse. Provides a unified constructor for all subclasses of :class:`RFPulse`. See also :func:`AreaPulse` for a higher level interface to pulses on a specified :class:`Transition`.

    Args:
        duration (float): The duration of the pulse in seconds.
        amplitude (float): The peak amplitude of the pulse, relative to full scale.
        phase (float, optional): The phase of the pulse in radians. Defaults to None, in which case the previous phase setting is maintained.
        frequency (float, optional): The frequency of the pulse in Hertz. Defaults to None, in which case the previous frequency setting is maintained.
        center (bool, optional): Whether to reduce the duration of the preceding and following :class:`Wait` commands `duration/2`. Will throw an error during compilation if the :class:`Wait` commands are too short or the pulse is not adjacent to at least one :class:`Wait` command. If there is only one neighboring :class:`Wait` command, its duration is reduced by `duration/2`. Defaults to False.
        window (RFPulse, optional): The shape of the pulse. Defaults to RectangularPulse.
        **kwargs: Additional keyword arguments, which are passed to window's `__init__` method

    Returns:
        RFPulse: An :class:`RFPulse` with the specified parameters
    """
    return window(duration, amplitude, phase, frequency, center, **kwargs)

def AreaPulse(area, amplitude=None, phase=None, center=False, window=RectangularPulse, **kwargs):
    """
    AreaPulse(area, amplitude=None, phase=None, center=False, window=RectangularPulse, **kwargs)

    High level function for generating an RF pulse on a specified :class:`Transition`, which must be set by a :class:`SetTransition` command before the first :func:`AreaPulse`. The pulse timing is calculated to provide the specified pulse `area`. See also :func:`Pulse` for a low level function for generating pulses with manually specified frequency, amplitude, and duration.

    Args:
        area (float): The pulse area in radians.
        amplitude (float, optional): The peak amplitude of the pulse, relative to full scale. Defaults to None, in which case the default amplitude for the specified :class:`Transition` is used.
        phase (float, optional): The phase of the pulse in radians. Defaults to None, in which case the previous phase setting is maintained.
        center (bool, optional): Whether to reduce the duration of the preceding and following :class:`Wait` commands `duration/2`. Will throw an error during compilation if the :class:`Wait` commands are too short or the pulse is not adjacent to at least one :class:`Wait` command. If there is only one neighboring :class:`Wait` command, its duration is reduced by `duration/2`. Defaults to False.
        window (RFPulse, optional): The shape of the pulse. Defaults to RectangularPulse.
        **kwargs: Additional keyword arguments, which are passed to window's `__init__` method

    Returns:
        RFPulse: An :class:`RFPulse` with the specified parameters
    """
    raise NotImplementedError

def PiPulse(amplitude=None, phase=None, center=False, window=RectangularPulse, **kwargs):
    """
    PiPulse(amplitude=None, phase=None, center=False, window=RectangularPulse, **kwargs)

    A wrapper for :func:`AreaPulse` with pulse area set to pi. Refer to :func:`AreaPulse` for full documentation.
    """
    return AreaPulse(pi, amplitude=None, phase=None, center=False, window=RectangularPulse, *kwargs)

def PiOver2Pulse(amplitude=None, phase=None, center=False, window=RectangularPulse, *kwargs):
    """
    PiOver2Pulse(amplitude=None, phase=None, center=False, window=RectangularPulse, **kwargs)

    A wrapper for :func:`AreaPulse` with pulse area set to pi/2. Refer to :func:`AreaPulse` for full documentation.
    """
    return AreaPulse(pi/2, amplitude=None, phase=None, center=False, window=RectangularPulse, **kwargs)

def SpinEcho(duration, pulse=None):
    """
    SpinEcho(duration, pulse=None)

    Returns a list of pulses and :class:`Wait` commands implementing a spin echo decoupling sequence consisting of a `duration/2` :class:`Wait`, a pi pulse about the `x` axis and another `duration/2` :class:`Wait`.

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

    Returns a list of pulses and :class:`Wait` commands implementing a Ramsey interferometry sequence, consisting of a pi/2 pulse with zero phase, a :class:`Wait` of length `duration`, and a final pi/2 pulse with phase `phase`. A decoupling sequence can optionally be inserted instead of the :class:`Wait`.

    Args:
        duration (float): The dark time (in seconds) for the Ramsey sequence.
        phase (float, optional): The phase of the final pulse. Defaults to 0.
        pulse (RFPulse, optional): The pulse to use for the pi/2 pulses in the Ramsey sequence. Should normally be generated by :func:`PiOver2Pulse`. The phase of the pulses are overridden in the sequence. Defaults to None, in which case a :class:`RectangularPulse` with the default amplitude and frequency for the selected :class:`Transition` is used.
        decoupling (list of :class:`RFBlock`, optional): A decoupling sequence (generated by :func:`XY8`, for example) to insert during the dark time. The duration of :class:`Wait` commands is adjusted to make the total length equal to `duration`. Defaults to None.

    Returns:
        list of :class:`RFBlock`: Returns a list of pulses and :class:`Wait` commands implementing a Ramsey sequence.
    """
    raise NotImplementedError()