import numpy as np
from synthesizer_sequences import PiOver2Pulse, PiPulse, Wait
from copy import deepcopy
from termcolor import colored


def validate_frame_matrix(frame_matrix):
    """Checks if a frame matrix is valid.

    Args:
        frame_matrix (np.ndarray): The 4xN toggling frame matrix. The first three rows correspond to the orientation of the original +Sz operator along the +X, +Y, +Z axes. Each column should have +/- 1 in one entry and zero in the others. The fourth row is the duration of that frame. See PHYSICAL REVIEW X 10, 031002 (2020) for details.

    Raises:
        ValueError: If the frame matrix is not valid.
    """
    if frame_matrix.shape[0] != 4:
        raise ValueError("The frame matrix must have 4 rows.")

    last_frame = np.array([0, 0, 0, None])
    for frame in frame_matrix.T:
        if frame[3] < 0:
            raise ValueError("The duration of each frame must be non-negative.")

        is_nonzero = False
        for i in range(3):
            if frame[i] != 0:
                if is_nonzero:
                    raise ValueError("Each frame must have exactly one non-zero entry.")
                is_nonzero = True
                if frame[i] != 1 and frame[i] != -1:
                    raise ValueError("Each non-zero entry must be +/- 1.")

            if frame[i] != 0 and last_frame[i] != 0 and frame[i] != last_frame[i]:
                raise ValueError("Two consecutive frames must be rotated by pi/2.")

        last_frame = frame


def frame_matrix_to_pulses(frame_matrix, pi2_pulse=PiOver2Pulse()):
    """Converts a toggling frame matrix to a list of pulses.

    Args:
        frame_matrix (np.ndarray): The 4xN toggling frame matrix. The first three rows correspond to the orientation of the original +Sz operator along the +X, +Y, +Z axes. Each column should have +/- 1 in one entry and zero in the others. The fourth row is the duration of that frame. If the duration is zero, it disambiguates the rotation direction to the next frame. See PHYSICAL REVIEW X 10, 031002 (2020) for details.
        pi2_pulse (Pulse): The pulse to use for a pi/2 rotation.
        initial_frame (np.ndarray): The initial frame. Defaults to np.array([0, 0, 1, 0]).
    Returns:
        list: A list of pulses.
    """

    validate_frame_matrix(frame_matrix)

    vx = np.array([1, 0, 0])
    vy = np.array([0, 1, 0])
    vz = np.array([0, 0, 1])
    initial_orientation = np.array([vx, -vx, vy, -vy, vz, -vz])
    orientation = deepcopy(initial_orientation)

    def rotate(orientation, phi):
        """
        Rotates the orientation by a pi/2 pulse with phase phi in the XY plane. If the phase is None, the orientation is not rotated.

        Args:
            orientation (np.ndarray): The orientation of the original +Sz operator along the +X, +Y, +Z axes.
            phi (float): The phase of the pi/2 pulse in the XY plane. Must be a multiple of pi/2 or None.

        Returns:
            np.ndarray: The rotated orientation.
        """

        if phi is None:
            return orientation

        phi = phi % (2 * np.pi)
        if np.isclose(phi, 0):
            return orientation[[0, 1, 5, 4, 2, 3]]
        elif np.isclose(phi, np.pi / 2):
            return orientation[[4, 5, 2, 3, 1, 0]]
        elif np.isclose(phi, np.pi):
            return orientation[[0, 1, 4, 5, 3, 2]]
        elif np.isclose(phi, 3 * np.pi / 2):
            return orientation[[5, 4, 2, 3, 0, 1]]
        else:
            raise ValueError(f"Phase must be a multiple of pi/2 or None but is {phi}.")

    def get_phi(frame, orientation):
        """
        Gets the phase of the pi/2 pulse that rotates the orientation to the next frame.

        Args:
            frame (np.ndarray): The frame.
            orientation (np.ndarray): The orientation of the original +Sz operator along the +X, +Y, +Z axes.

        Returns:
            float: The phase of the pi/2 pulse in the XY plane. Must be a multiple of pi/2 or None.
        """

        phis = [0, np.pi / 2, np.pi, 3 * np.pi / 2, None]
        for phi in phis:
            new_z = rotate(orientation, phi)[4]
            if all(new_z == frame[:3]):
                return phi
        raise ValueError("The frame matrix is invalid.")

    pulses = []
    for frame in frame_matrix.T:
        phi = get_phi(frame, orientation)
        if phi is not None:
            phased_pulse = deepcopy(pi2_pulse)
            phased_pulse.phase = phi
            pulses.append(phased_pulse)
            orientation = rotate(orientation, phi)
        if frame[3] != 0:
            pulses.append(Wait(frame[3]))

    return pulses


def display_frame_matrix(frame_matrix):
    """
    Displays a toggling frame matrix, following the convention of PHYSICAL REVIEW X 10, 031002 (2020).

    Frames of nonzero diration are shown using █ and frames of zero duration using |. +1 is shown as yellow, -1 as green, and 0 as white.

    Args:
        frame_matrix (np.ndarray): The frame matrix.
    """

    for row in range(3):
        for col in range(frame_matrix.shape[1]):
            if frame_matrix[3, col] == 0:
                symbol = "|"
            else:
                symbol = "█"
            if frame_matrix[row, col] == 1:
                print(colored(symbol, "yellow", "on_white"), end="")
            elif frame_matrix[row, col] == -1:
                print(colored(symbol, "green", "on_white"), end="")
            else:
                print(colored(symbol, "white", "on_white"), end="")
        print()


def display_pulses(pulses):
    """
    Displays a list of pulses, following the convention of PHYSICAL REVIEW X 10, 031002 (2020).

    Waits are shown as " " and pi/2 pulses as "█". Pulses about the +/-X axis are red, and about the +/-Y axis are blue. Pulses about a + axis are in the top row, and pulses about a - axis are in the bottom row.

    Args:
        pulses (list): The list of pulses.
    """

    for row in range(2):
        for pulse in pulses:
            if isinstance(pulse, Wait):
                symbol = " "
            else:
                symbol = "█"
            if pulse.phase == 0 or pulse.phase == np.pi:
                color = "red"
            else:
                color = "blue"
            if pulse.phase == 0 or pulse.phase == np.pi / 2:
                pulse_row = 0
            else:
                pulse_row = 1
            if row == pulse_row:
                print(colored(symbol, color, "on_white"), end="")
            else:
                print(colored(" ", "white", "on_white"), end="")
        print()


def DROID_R2D2(tx, ty=None, tz=None):
    """
    Generates the frame matrix for the DROID-R2D2 sequence as described in PHYSICAL REVIEW LETTERS 130, 210403 (2023).

    Args:
        tx (float): The time to spend in the +/-X frame.
        ty (float): The time to spend in the +/-Y frame. Defaults to None, in which case tx is used.
        tz (float): The time to spend in the +/-Z frame. Defaults to None, in which case tx is used.
    """

    if ty is None:
        ty = tx
    if tz is None:
        tz = tx

    def x(t=0):
        return np.array([1, 0, 0, t])

    def y(t=0):
        return np.array([0, 1, 0, t])

    def z(t=0):
        return np.array([0, 0, 1, t])

    def mx(t=0):
        return np.array([-1, 0, 0, t])

    def my(t=0):
        return np.array([0, -1, 0, t])

    def mz(t=0):
        return np.array([0, 0, -1, t])

    frame_matrix = np.array(
        [
            z(tz),
            my(),
            mz(tz),  # Z
            y(),
            mx(tx),
            z(),
            x(tx),  # X
            mz(),
            my(ty),
            x(),
            y(ty),  # Y
            mx(),
            mz(tz),
            y(),
            z(tz),  # Z
            my(),
            mx(tx),
            mz(),
            x(tx),  # X
            z(),
            y(ty),
            mx(),
            my(ty),  # Y
            x(),
            mz(tz),
            my(),
            z(tz),  # Z
            y(),
            x(tx),
            z(),
            mx(tx),  # X
            mz(),
            y(ty),
            x(),
            my(ty),  # Y
            mx(),
            z(tz),
            y(),
            mz(tz),  # Z
            my(),
            x(tx),
            mz(),
            mx(tx),  # X
            z(),
            my(ty),
            mx(),
            y(ty),  # Y
            x(),
            my(ty),
            x(),
            y(ty),  # Y
            mz(),
            x(tx),
            z(),
            mx(tx),  # X
            y(),
            z(tz),
            my(),
            mz(tz),  # Z
            x(),
            y(ty),
            mx(),
            my(ty),  # Y
            z(),
            x(tx),
            mz(),
            mx(tx),  # X
            my(),
            mz(tz),
            y(),
            z(tz),  # Z
            mx(),
            y(ty),
            x(),
            my(ty),  # Y
            mz(),
            mx(tx),
            z(),
            x(tx),  # X
            y(),
            mz(tz),
            my(),
            z(tz),  # Z
            x(),
            my(ty),
            mx(),
            y(ty),  # Y
            z(),
            mx(tx),
            mz(),
            x(tx),  # X
            my(),
            z(tz),
            y(),
            mz(tz),  # Z
            mx(),
        ]
    ).T
    return frame_matrix