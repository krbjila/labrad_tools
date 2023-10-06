from typing import List, Dict, Union
from dataclasses import dataclass, field
from math import pi

import synthesizer_sequences_base as ssb

INSTRUCTION_ADDRESS_SIZE = 14
MAX_INSTRUCTION_ADDRESS = 2**INSTRUCTION_ADDRESS_SIZE - 1
INSTRUCTION_SIZE = 128
REGISTER_ADDRESS_SIZE = 16
REGISTER_SIZE = 32
N_COUNTERS = 8

F_MAX = 307.2e6
F_BITS = 32
P_BITS = 12
A_BITS = 16
T_MIN = 1 / 153.6e6
T_BITS = 48
T_MAX = T_MIN * (2**T_BITS - 1)


@dataclass
class Node:
    visited: bool = False
    children: List["Node"] = field(default_factory=list)
    start: int = 0
    end: int = 0

    def __len__(self):
        return sum(len(c) for c in self.children)

    def compile(self, state: Dict[str, ssb.RFUpdate]):
        """
        Generates a dictionary of synthesizer commands for the block. Modifies state to the state of the channels after the block.

        Args:
            state (Dict[str, ssb.RFUpdate]): The current state of the channels

        Returns:
            List[bytearray]: A list of synthesizer commands.
            float: The time after the block
        """
        raise NotImplementedError


@dataclass
class BasicBlock(Node):
    instructions: List[ssb.Timestamp] = field(default_factory=list)

    def __len__(self):
        # Number of instructions
        return len(self.instructions)

    def compile(self, state: Dict[str, ssb.RFUpdate]):
        time = 0
        instructions = []
        for i, ts in enumerate(self.instructions):
            state.update(ts.update)
            address = self.start + i
            instructions.append(timestamp(ts.update, time, address))
            time += ts.duration
        return instructions, time


@dataclass
class Loop(Node):
    n: int = 0
    counter: int = 0

    def __len__(self):
        # Number of instructions
        return sum(len(c) for c in self.children) + 4

    def compile(self, state: Dict[str, ssb.RFUpdate]):
        length = sum(len(c) for c in self.children)
        instructions = compile_loop(self.start, length, self.n, self.counter)
        return instructions

@dataclass
class Subroutine(Node):
    element_hash: int = 0
    counter: int = 0
    subroutine_start: int = 0
    subroutine_end: int = 0

    def __len__(self):
        # Number of instructions in the sequence. The subroutine itself is not counted.
        return 3

    def compile(self, state: Dict[str, ssb.RFUpdate]):
        length = sum(len(c) for c in self.children)
        instructions = compile_subroutine(
            self.start, self.subroutine_start, self.counter
        )
        return instructions


def generate_instructions(sequence: ssb.Sequence) -> Dict[str, List[bytearray]]:
    """
    Compiles a sequence into a list of instructions for each channel group.

    Each instruction is a bytearray of length INSTRUCTION_SIZE // 8.

    Args:
        sequence (Sequence): Sequence to compile

    Returns:
        Dict[str, Dict[int, bytearray]]: Dictionary with keys channel group names and values dictionaries of addresses and instructions
    """

    instructions = {}
    for group, channels in ssb.CHANNEL_GROUPS.items():
        print(f"Compiling channel group {group}...")

        compiled = sequence.compile(channels)
        if not isinstance(compiled, ssb.Sequence):
            compiled = ssb.Sequence(compiled)

        # Build a graph of the sequence
        stack = [Node()]
        subroutines = []
        loops = []
        instruction_stack = [compiled]
        while len(instruction_stack):
            element = instruction_stack.pop()
            if isinstance(element, ssb.Sequence):
                instruction_stack.extend(reversed(element.elements))
            if isinstance(element, ssb.Timestamp):
                if not isinstance(stack[-1], BasicBlock):
                    block = BasicBlock()
                    stack[-1].children.append(block)
                    stack.append(block)
                stack[-1].instructions.append(element)
            if element == "return":
                if isinstance(stack[-1], BasicBlock):
                    stack.pop()
                node = stack.pop()
                if isinstance(node, Loop):
                    loops.append(node)
            if isinstance(element, ssb.Subroutine) or isinstance(element, ssb.Repeat):
                if isinstance(stack[-1], BasicBlock):
                    stack.pop()
                if isinstance(element, ssb.Subroutine):
                    exists = False
                    for subroutine in subroutines:
                        if subroutine.element_hash == hash(element):
                            exists = True
                            node = subroutine
                            break
                    if not exists:
                        node = Subroutine(element_hash=hash(element))
                        subroutines.append(node)
                else:
                    node = Loop(n=element.times)
                stack[-1].children.append(node)
                stack.append(node)
                instruction_stack.append("return")
                instruction_stack.append(element.sequence)

        # Traverse the graph to assign counters
        root = stack[0]
        stack = [n for n in root.children]
        while len(stack):
            node = stack.pop()
            if isinstance(node, Subroutine):
                assert node in subroutines
            if isinstance(node, Loop) or isinstance(node, Subroutine):
                if node.visited:
                    for child in node.children:
                        if isinstance(child, Loop) or isinstance(child, Subroutine):
                            node.counter = max(node.counter, child.counter + 1)
                            if node.counter >= N_COUNTERS:
                                raise Exception(
                                    f"Too many nested loops or subroutines in channel group {group}"
                                )
                else:
                    node.visited = True
                    stack.append(node)
                    stack.extend(node.children)

        # Assign addresses to subroutines
        address = MAX_INSTRUCTION_ADDRESS - 1
        for subroutine in subroutines:
            length = (
                sum(len(c) for c in subroutine.children) + 1
            )  # +1 for the return instruction
            subroutine.subroutine_start = address - length
            subroutine.subroutine_end = address
            address -= length
            if address < 0:
                raise Exception(
                    f"Subroutines in channel group {group} too long to fit in memory"
                )
        min_subroutine_address = address

        # Assign memory addresses to sequence
        address = 0
        stack = [n for n in root.children]
        while len(stack):
            node = stack.pop()
            if isinstance(node, BasicBlock):
                node.start = address
                node.end = address + len(node) - 1
                address += len(node)
            elif isinstance(node, Loop):
                node.start = address
                node.end = address + len(node) - 1
                address += 3
                stack.append("return")
                stack.extend(reversed(node.children))
            elif isinstance(node, Subroutine):
                node.start = address
                node.end = address + len(node) - 1
                address += 3
            elif node == "return":
                address += 1
            if address >= min_subroutine_address - 1:
                raise Exception(
                    f"Sequence in channel group {group} too long to fit in memory"
                )

        instructions[group] = {}
        state = {}
        for channel in channels:
            if "RF" in channel:
                state[channel] = ssb.DEFAULT_RF_UPDATE
            elif "D" in channel:
                state[channel] = ssb.DEFAULT_DIGITAL_UPDATE

        # Traverse the graph to generate instructions
        # TODO: implement!


def timestamp(update: Dict[str, Union[ssb.RFUpdate, ssb.DigitalUpdate]], time: float, address: int) -> bytearray:
    """
    timestamp(timestamp)

    Converts a timestamp to a list of instructions for programming the synthesizer

    Args:
        update (Dict[str, Union[ssb.RFUpdate, ssb.DigitalUpdate]]): The state of the channels to be set
        time (float): The timestamp's start time, in seconds
        address (int): The address of the timestamp

    Returns:
        bytearray: The corresponding instruction
    """
    raise NotImplementedError

    # buffers = []
    # for i in range(4):
    #     b = bytearray(8)
    #     b[0] = 0xA1  # Start bits
    #     b[1] = 2**4 * i + channel  # Memory, channel
    #     b[2:4] = address.to_bytes(2, "big")
    #     buffers.append(b)

    #     # Timestamp & digital outputs
    #     ttw = t_to_timestamp(timestamp.duration)
    #     if set_digital:
    #         for i in range(ssb.MAX_DIGITAL_CHANNEL):
    #             ttw += digital_out[i] * 2 ** (56 + i)
    #     ttw = ttw.to_bytes(8, "big")

    #     buffers[0][4:] = ttw[4:]
    #     buffers[1][4:] = ttw[:4]
    #     buffers[1][5] += wait_for_trigger


@staticmethod
def f_to_ftw(f):
    """
    f_to_ftw(f)

    Converts a frequency in Hertz to the format required for programming the synthesizer

    Args:
        f (float): The frequency in Hertz

    Raises:
        ValueError: Raises an error if the frequency is less than zero or greater than the maximum frequency

    Returns:
        int: The 32-bit unsigned integer corresponding to f
    """
    if f < 0 or f > F_MAX * (2**F_BITS - 1) / 2**F_BITS:
        raise ValueError(
            "Frequency of {} Hz outside valid range of 0 to {} Hz".format(f, F_MAX)
        )
    f_int = round((f / F_MAX) * (2**F_BITS - 1))
    return f_int


@staticmethod
def a_to_atw(a):
    """
    a_to_atw(a)

    Converts an amplitude to the format required for programming the synthesizer

    Args:
        a (float): The amplitude, relative to full scale

    Raises:
        ValueError: Raises an error if the amplitude is less than zero or greater than one

    Returns:
        int: The 16-bit unsigned integer corresponding to a
    """
    if a < 0 or a > 1:
        raise ValueError("Amplitude of {} outside valid range of 0 to 1".format(a))
    a_int = round(a * (2**A_BITS - 1))
    return a_int


@staticmethod
def t_to_timestamp(t):
    """
    t_to_timestamp(t)

    Converts a time to the format required for programming the synthesizer

    Args:
        t (float): The time, in seconds

    Raises:
        ValueError: Raises an error if the time is less than zero or greater than 27.962 seconds

    Returns:
        int: The 48-bit unsigned integer corresponting to t
    """
    if t < 0 or t > T_MAX:
        raise ValueError(
            "Time step of {} s outside valid range of 0 to {} s".format(t, T_MAX)
        )
    t_int = round(t / T_MIN)
    return t_int


@staticmethod
def phase_to_ptw(phi):
    """
    phase_to_ptw(phi)

    Converts a phase to the format required for programming the synthesizer

    Args:
        phi (float): The phase in radians.

    Returns:
        int: The 12-bit unsigned integer corresponting to phi
    """
    a_int = round((phi % (2 * pi)) / (2 * pi) * (2**P_BITS - 1))
    return a_int


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


def compile_loop(start: int, length: int, n: int, counter: int) -> List[bytearray]:
    """
    Args:
        start (int): First address of the loop
        length (int): Number of instructions in the loop
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
        subroutine_end (int): Last address of the subroutine (which will be used for a conditional jump instruction)
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
    # Add the jump

    return instructions
