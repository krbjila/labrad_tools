from abc import ABC, abstractmethod
from typing import List, Set, Dict, Union
from typing import NamedTuple
import re
from copy import copy, deepcopy
from collections import deque
from dataclasses import dataclass, field


MAX_FREQUENCY = 307.2e6  # Hertz
MIN_DURATION = 1 / 153.6e6  # seconds
MAX_DURATION = 2**48 * MIN_DURATION  # seconds
MAX_RF_CHANNEL = 3
MAX_DIGITAL_CHANNEL = 6

RF_CHANNELS = {f"RF{i}" for i in range(MAX_RF_CHANNEL + 1)}
DIGITAL_CHANNELS = {f"D{i}" for i in range(MAX_DIGITAL_CHANNEL + 1)}
CHANNELS = RF_CHANNELS | DIGITAL_CHANNELS
CHANNEL_GROUPS = {"RF0D": {"RF0"} | DIGITAL_CHANNELS}
for i in range(1, MAX_RF_CHANNEL + 1):
    CHANNEL_GROUPS[f"RF{i}"] = {f"RF{i}"} | DIGITAL_CHANNELS


def validate_channel(channel: str):
    if channel not in CHANNELS:
        raise ValueError(f"Channel must be one of {CHANNELS}")


class RFUpdate(NamedTuple):
    """
    Attributes:
        frequency (float): Frequency in Hertz
        phase (float): Phase in radians
        amplitude (float): Amplitude as a fraction of the maximum amplitude
        offset (float): LO frequency in Hertz. This is not controlled by the synthesizer but is used to calculate the IF frequency.
    """

    frequency: Union[float, None] = None
    phase: Union[float, None] = None
    amplitude: Union[float, None] = None
    offset: float = 0

    def __post_init__(self):
        self.validate()

    def validate(self):
        if self.frequency is not None and (
            self.frequency - self.offset > MAX_FREQUENCY
            or self.frequency - self.offset < 0
        ):
            raise ValueError("Frequency must be non-negative")
        if self.phase is not None:
            try:
                float(self.phase)
            except ValueError:
                raise ValueError("Phase must be a float")
        if self.amplitude is not None and (self.amplitude < 0 or self.amplitude > 1):
            raise ValueError("Amplitude must be between 0 and 1")


class DigitalUpdate(NamedTuple):
    """
    Attributes:
        value (bool): Value of the digital channel
    """

    value: Union[bool, None] = None

    def validate(self):
        if self.value is not None:
            try:
                bool(self.value)
            except ValueError:
                raise ValueError("Value must be a boolean")


class SequenceElement(ABC):
    @property
    @abstractmethod
    def duration(self) -> float:
        """Duration of the sequence element in seconds"""
        raise NotImplementedError

    @property
    @abstractmethod
    def channels(self) -> Set[str]:
        """The set of channels used by the sequence element"""
        raise NotImplementedError

    def compile(self, channels: Set[str]) -> "SequenceElement":
        return self

    @abstractmethod
    def __repr__(self) -> str:
        raise NotImplementedError

    def __add__(self, other: "SequenceElement") -> "Sequence":
        return Sequence(self, other)

    def __radd__(self, other: "SequenceElement") -> "Sequence":
        return Sequence(other, self)

    def __mul__(self, other: int) -> "Repeat":
        return Repeat(self, other)

    def __rmul__(self, other: int) -> "Repeat":
        return self.__mul__(other)

    def __eq__(self, __value: object) -> bool:
        return repr(self) == repr(__value)

    def __hash__(self) -> int:
        return hash(repr(self))


class Sequence(SequenceElement):
    def __init__(self, *elements: SequenceElement):
        self.elements = elements

    @property
    def duration(self) -> float:
        return sum(element.duration for element in self.elements)

    @property
    def channels(self) -> Set[str]:
        return set.union(*[element.channels for element in self.elements])

    def __repr__(self) -> str:
        return f"Sequence({', '.join(repr(element) for element in self.elements)})"

    def compile(self, channels) -> "Sequence":
        if not self.channels & channels:
            return Timestamp(self.duration)

        compiled = Sequence(*[element.compile(channels) for element in self.elements])

        # Combines adjacent timestamps into a single timestamp if they have the same update and unpacks nested sequences
        # If a timestamp has length zero, its update is combined with the next timestamp
        new_elements = []
        stack = [i for i in reversed(compiled.elements)]
        while len(stack):
            element = stack.pop()
            if isinstance(element, Sequence):
                stack.extend(reversed(element.elements))
                continue
            elif isinstance(element, Timestamp):
                update = {
                    channel: setting
                    for channel, setting in element.update.items()
                    if channel in channels
                }
                if (
                    len(new_elements)
                    and isinstance(new_elements[-1], Timestamp)
                    and new_elements[-1].duration + element.duration <= MAX_DURATION
                ):
                    if update == new_elements[-1].update:
                        new_elements[-1].duration += element.duration
                        continue
                    elif new_elements[-1].duration == 0:
                        new_elements[-1].duration = element.duration
                        new_elements[-1].update = new_elements[-1].update | update
                        continue
            new_elements.append(element)
        return Sequence(*new_elements)


class Parallel(SequenceElement):
    def __init__(self, *elements: SequenceElement):
        raise NotImplementedError
        self.elements = elements

    @property
    def elements(self) -> Set[SequenceElement]:
        return self._elements

    @elements.setter
    def elements(self, elements: Set[SequenceElement]):
        if not elements:
            raise ValueError("Parallel sequence must have at least one element")

        channels = set()
        channel_groups = set()
        for element in elements:
            for group, group_channels in CHANNEL_GROUPS.items():
                if any(channel in group_channels for channel in element.channels):
                    if group in channel_groups:
                        raise ValueError(
                            f"Multiple elements of parallel sequence use channel group {group}"
                        )
                    channel_groups.add(group)
            channels.update(element.channels)

        self._elements = {elements.compile(channels) for elements in elements}
        self._channels = channels
        self._duration = max(element.duration for element in elements)

    @property
    def duration(self) -> float:
        return self._duration

    @property
    def channels(self) -> Set[str]:
        return self._channels

    def compile(self, channels: Union[Set[str], None] = None) -> "Sequence":
        raise NotImplementedError
        # add padding to each element to make them all the same duration
        elements = set()
        for element in self.elements:
            if element.duration < self.duration:
                element = Sequence(element, Timestamp(self.duration - element.duration))
            elements.add(element.compile())

        # build a sequence by interleaving the parallel elements, taking the earliest timestamp at each step
        # TODO: this is a little bit complicated because we need to properly handle loops and subroutines

    def __repr__(self) -> str:
        return f"Parallel({', '.join(repr(element) for element in self.elements)})"


class Repeat(SequenceElement):
    def __init__(self, sequence: SequenceElement, times: int):
        self.sequence = sequence
        self.times = times

    @property
    def times(self) -> int:
        return self._times

    @times.setter
    def times(self, times: int):
        if not isinstance(times, int):
            raise TypeError("Times must be an integer")
        if times < 0:
            raise ValueError("Times must be non-negative")
        self._times = times

    @property
    def duration(self) -> float:
        return self.sequence.duration * self._times

    @property
    def channels(self) -> Set[str]:
        return self.sequence.channels

    def compile(self, channels) -> "SequenceElement":
        if not self.channels & channels:
            return Timestamp(self.duration)

        if isinstance(self.sequence, Repeat):
            return Repeat(
                self.sequence.sequence.compile(channels),
                self._times * self.sequence.times,
            )
        elif isinstance(self.sequence, Timestamp):
            return Timestamp(
                self.sequence.duration * self._times, self.sequence.update
            ).compile(channels)
        else:
            return Repeat(self.sequence.compile(channels), self._times)

    def __mul__(self, other: int) -> "Repeat":
        return Repeat(self.sequence, self._times * other)

    def __rmul__(self, other: int) -> "Repeat":
        return Repeat(self.sequence, self._times * other)

    def __repr__(self) -> str:
        return f"Repeat({repr(self.sequence)}, {self._times})"


class Subroutine(SequenceElement):
    def __init__(self, sequence: SequenceElement):
        self.sequence = sequence

    @property
    def duration(self) -> float:
        return self.sequence.duration

    @property
    def channels(self) -> Set[str]:
        return self.sequence.channels

    def compile(self, channels) -> "SequenceElement":
        if not self.channels & channels:
            return Timestamp(self.duration)
        else:
            return Subroutine(self.sequence.compile(channels))

    def __repr__(self) -> str:
        return f"Subroutine({repr(self.sequence)})"


class WaitForTrigger(SequenceElement):
    @property
    def duration(self) -> float:
        return 0

    @property
    def channels(self) -> Set[str]:
        return set()

    def __repr__(self) -> str:
        return "WaitForTrigger()"


class Timestamp(SequenceElement):
    _update: Dict[str, Union["RFUpdate", "DigitalUpdate"]]

    def __init__(
        self,
        duration: float,
        update: Dict[str, Union["RFUpdate", "DigitalUpdate"]] = dict(),
    ):
        """
        Args:
            duration (float): Duration of the timestamp in seconds
            update (dict): Dictionary with keys as channel names and values as channel settings
        """
        self.update = update
        self.duration = duration

    @property
    def update(self) -> Dict[str, Union["RFUpdate", "DigitalUpdate"]]:
        return self._update

    @update.setter
    def update(self, update: Dict[str, Union["RFUpdate", "DigitalUpdate"]]):
        for channel, setting in update.items():
            validate_channel(channel)
            setting.validate()
        self._update = update
        self._channels = set(update.keys())

    @property
    def duration(self) -> float:
        return self._duration

    @duration.setter
    def duration(self, duration: float):
        if duration < 0 or duration > MAX_DURATION:
            raise ValueError(f"Duration must be between 0 and {MAX_DURATION} seconds")
        self._duration = duration

    @property
    def channels(self) -> Set[str]:
        return self._channels

    def __repr__(self) -> str:
        if self.update:
            return f"Timestamp({self.duration}, {self.update})"
        else:
            return f"Timestamp({self.duration})"

    def compile(self, channels: Set[str]) -> "Timestamp":
        return Timestamp(
            self.duration,
            {
                channel: setting
                for channel, setting in self.update.items()
                if channel in channels
            },
        )
