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
MAX_ADDRESS = 2**14 - 1

RF_CHANNELS = {f"RF{i}" for i in range(MAX_RF_CHANNEL + 1)}
DIGITAL_CHANNELS = {f"D{i}" for i in range(MAX_DIGITAL_CHANNEL + 1)}
CHANNELS = RF_CHANNELS | DIGITAL_CHANNELS
CHANNEL_GROUPS = {"RF0D": {"RF0"} | DIGITAL_CHANNELS}
for i in range(1, MAX_RF_CHANNEL + 1):
    CHANNEL_GROUPS[f"RF{i}"] = {f"RF{i}"} | DIGITAL_CHANNELS


def validate_channel(channel: str):
    if not isinstance(channel, str) or not channel:
        raise TypeError("Channel must be a non-empty string")

    match = re.match(r"(RF|D)(\d+)", channel)
    if not match:
        raise ValueError(f"Channel {channel} must be of the form (RF|D)\\d+")
    if match.group(1) == "RF":
        if int(match.group(2)) > MAX_RF_CHANNEL:
            raise ValueError(
                f"RF channel number must be between 0 and {MAX_RF_CHANNEL}"
            )
    elif match.group(1) == "D":
        if int(match.group(2)) > MAX_DIGITAL_CHANNEL:
            raise ValueError(
                f"Digital channel number must be between 0 and {MAX_DIGITAL_CHANNEL}"
            )


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

    def to_instructions(self) -> Dict[str, List[bytearray]]:
        """
        Compiles a sequence into a list of instructions for each channel group. Each instruction is a bytearray of length 16.

        Args:
            sequence (SequenceElement): Sequence to compile
        """

        timestamps = {}
        for group, channels in CHANNEL_GROUPS.items():
            print(f"Channel group {group}")
            timestamps[group] = []

            @dataclass
            class Node:
                element: Union["Subroutine", "Repeat", None]
                children: List["Node"] = field(default_factory=list)
                counter: int = -1

            # Build a tree of subroutines and loops
            stack = [self.compile(channels)]
            routines = {}
            root_node = Node(None)
            routine_stack = [root_node]
            while len(stack):
                element = stack.pop()
                if isinstance(element, Sequence):
                    stack.extend(reversed(element.elements))
                elif isinstance(element, Subroutine) or isinstance(element, Repeat):
                    if element not in routines:
                        routines[element] = Node(element)
                        routine_stack[-1].children.append(routines[element])
                        routine_stack.append(routines[element])
                        stack.append("end")
                        stack.append(element.sequence)
                elif element == "end":
                    routine_stack.pop()

            for routine, node in routines.items():
                print(
                    f"Routine {routine.__hash__() % 1000} has children {[child.element.__hash__() % 1000 for child in node.children]}"
                )

            queue = deque([root_node]) if root_node.children else deque()
            while len(queue):
                node = queue.popleft()
                if node.counter < 0:  # node has not been visited yet
                    print(f"Visiting node {node.element.__hash__() % 1000}")
                    node.counter = 0
                    queue.extend(node.children)
                    queue.append(node)
                elif node.children:  # node has been visited and has children
                    print(
                        f"Revisiting node {node.element.__hash__() % 1000} with children {[child.element.__hash__() % 1000 for child in node.children]}"
                    )
                    node.counter = max(child.counter for child in node.children) + 1
                    print(f"Node counter is now {node.counter}")
                else:  # node has been visited and has no children
                    print(
                        f"Revisiting node {node.element.__hash__() % 1000} with no children"
                    )
                    node.counter = 0

            for routine, node in routines.items():
                print(f"Routine {routine.__hash__() % 1000} has counter {node.counter}")


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


INSTRUCTION_ADDRESS_SIZE = 14
INSTRUCTION_SIZE = 64
REGISTER_ADDRESS_SIZE = 16
REGISTER_SIZE = 32
N_COUNTERS = 8


def set_register(register: int, value: int) -> bytearray:
    """
    Returns an instruction to set a register to a value.

    Bits [0:31]: register value
    Bits [32:47]: register address
    Bits [48:61]: 0
    Bits [62:63]: 0b01 (set register)

    Args:
        register (int): Register number
        value (int): Value to set the register to
    """
    assert 0 <= register < 2**REGISTER_ADDRESS_SIZE
    assert 0 <= value < 2**REGISTER_SIZE

    instruction = bytearray(INSTRUCTION_SIZE // 8)
    instruction[0:32] = value.to_bytes(4, byteorder="little")
    instruction[32:48] = register.to_bytes(2, byteorder="little")
    instruction[62:64] = b"\x01"

    return instruction


def jump(address: int) -> bytearray:
    """
    Returns an instruction to jump to an address.

    Bits [0:31]: 0
    Bits [32:47]: address
    Bits [48:61]: 0
    Bits [62:63]: 0b11 (jump)

    Args:
        address (int): Address to jump to
    """
    assert 0 <= address < 2**INSTRUCTION_ADDRESS_SIZE

    instruction = bytearray(INSTRUCTION_SIZE // 8)
    instruction[32:48] = address.to_bytes(2, byteorder="little")
    instruction[62:64] = b"\x03"

    return instruction


def conditional_jump(counter: int) -> bytearray:
    """
    Returns an instruction to jump to the address stored in register 0x20 + counter if register 0x00 + counter is not zero and register 0x10 + counter otherwise. Decrements register 0x00 + counter.

    Bits [0:31]: 0
    Bits [32:47]: 0x00 + counter
    Bits [48:61]: 0
    Bits [62:63]: 0b10 (conditional jump)
    """

    assert 0 <= counter < N_COUNTERS

    instruction = bytearray(INSTRUCTION_SIZE // 8)
    instruction[32:48] = (0x00 + counter).to_bytes(2, byteorder="little")
    instruction[62:64] = b"\x02"

    return instruction


def compile_loop(
    start: int, sequence: List[bytearray], n: int, counter: int
) -> List[bytearray]:
    """
    Args:
        start (int): First address of the loop
        sequence (List[bytearray]): List of instructions to be repeated
        n (int): Number of times to repeat the loop
        counter (int): Which counter to use for the loop
    """
    assert 0 <= start
    assert len(sequence) > 0
    assert start + len(sequence) + 3 <= 2**INSTRUCTION_ADDRESS_SIZE
    assert 1 <= n < 2**REGISTER_SIZE
    assert 0 <= counter < N_COUNTERS

    instructions = []

    # Set the loop counter
    instructions.append(set_register(0x00 + counter, n))
    # Set the loop end address
    instructions.append(set_register(0x10 + counter, start + len(sequence) + 3))
    # Set the loop start address
    instructions.append(set_register(0x20 + counter, start))
    # Loop
    instructions.extend(sequence)
    # Conditional jump
    instructions.append(conditional_jump(counter))

    return instructions


def compile_subroutine(
    start: int, subroutine_start: int, counter: int
) -> List[bytearray]:
    """
    Args:
        start (int): Address from which the subroutine is called
        subroutine_start (int): First address of the subroutine
        counter (int): Which counter to use for the subroutine
    """
    assert 0 <= start < 2**INSTRUCTION_ADDRESS_SIZE
    assert 0 <= subroutine_start < 2**INSTRUCTION_ADDRESS_SIZE
    assert 0 <= counter < N_COUNTERS

    instructions = []

    # Set the counter to zero
    instructions.append(set_register(0x00 + counter, 0))
    # Set the end address
    instructions.append(set_register(0x10 + counter, start + 3))
    # Jump to the subroutine
    instructions.append(jump(subroutine_start))

    return instructions
