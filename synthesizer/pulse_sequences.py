from math import isclose
import numpy as np
from pandas import Timestamp
from scipy.spatial.transform import Rotation as R
from synthesizer_sequences import AreaPulse, PiOver2Pulse, PiPulse, Wait
from copy import deepcopy
from termcolor import colored
# from colorama import just_fix_windows_console

# just_fix_windows_console()

 
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


def check_decoupling(frame_matrix, tp=0):
    """Checks if the pulses decouple different kinds of disorder, as described in Table 1 of PRX 10, 031002 (2020).

    Args:
        frame_matrix (np.ndarray): The 4xN toggling frame matrix. The first three rows correspond to the orientation of the original +Sz operator along the +X, +Y, +Z axes. Each column should have +/- 1 in one entry and zero in the others. The fourth row is the duration of that frame in seconds.
        tp (float): The duration of a pi/2 pulse in seconds. Defaults to 0.

    Returns:
        dict: A dictionary of conditions. The keys are the names of the conditions, and the values are booleans indicating whether the conditions are satisfied.
    """

    conditions = {}

    # Decoupling of on-siite disorder and antisymmetric spin exchange
    # Weighted row sum = 0
    conditions["On-site disorder and antisymmetric spin exchange"] = np.allclose(
        np.sum(frame_matrix[:3, :] * (frame_matrix[3, :] + (4 / np.pi) * tp), axis=1), 0
    )

    # Symmetrization of Ising interaction and symmetric spin exchange
    # Weighted absolute row sum equal between rows
    V = np.sum(np.abs(frame_matrix[:3, :]) * (frame_matrix[3, :] + tp), axis=1)
    conditions["Ising interaction and symmetric spin exchange"] = (
        np.isclose(V[0], V[1]) and np.isclose(V[1], V[2]) and np.isclose(V[2], V[0])
    )

    # Decoupling of interaction cross terms
    # Parity sum = 0 for each pair of rows
    satisfied = True
    for mu in range(3):
        for nu in range(mu):
            sum = np.sum(
                np.roll(frame_matrix[mu, :], -1) * frame_matrix[nu, :]
                + np.roll(frame_matrix[nu, :], -1) * frame_matrix[mu, :]
            )
            satisfied = satisfied and np.isclose(sum, 0)
    conditions["Interaction cross terms"] = satisfied

    # Suppression of rotation-angle error
    # Chirality sum = 0 for each pair of rows
    V = np.zeros(3)
    for k in range(frame_matrix.shape[1]):
        V += np.cross(
            frame_matrix[:3, (k + 1) % frame_matrix.shape[1]], frame_matrix[:3, k]
        )

    conditions["Rotation-angle error"] = np.allclose(V, np.zeros(3))

    return conditions


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

    nrows = frame_matrix.shape[0]
    for row in range(nrows - 1):
        for col in range(frame_matrix.shape[1]):
            if frame_matrix[nrows - 1, col] == 0:
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

    # TODO: This is kind of broken

    new_pulses = []
    for pulse in pulses:
        if "Wait" not in str(type(pulse)) and np.isclose(pulse.pulse_area, np.pi):
            new_pulses.append(
                PiOver2Pulse(pulse.amplitude, pulse.phase, pulse.frequency)
            )
            new_pulses.append(
                PiOver2Pulse(pulse.amplitude, pulse.phase, pulse.frequency)
            )
        else:
            new_pulses.append(pulse)

    for row in range(2):
        for pulse in new_pulses:
            if "Wait" in str(type(pulse)):
                print(colored(" ", "white", "on_white"), end="")
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


def opt_6tau(tau):
    """
    Minimal pulse sequence decoupling all leading-order interactions. See PHYSICAL REVIEW X 10, 031002 (2020) for details.

    Args:
        tau (float): The time to spend in each frame in seconds.


    Returns:
        np.ndarray: The frame matrix.
    """

    return np.array(
        [
            [0, 0, 1, tau],
            [0, 1, 0, tau],
            [1, 0, 0, 0],
            [0, 0, -1, 0],
            [0, -1, 0, tau],
            [-1, 0, 0, 0],
            [0, 0, -1, tau],
            [0, 1, 0, 0],
            [-1, 0, 0, tau],
            [0, 0, 1, 0],
            [0, -1, 0, 0],
            [1, 0, 0, tau],
        ]
    ).T


def DROID_R2D2(tx, ty=None, tz=None):
    """
    Generates the frame matrix for the DROID-R2D2 sequence as described in PHYSICAL REVIEW LETTERS 130, 210403 (2023).

    Args:
        tx (float): The time in seconds to spend in the +/-X frame in each instance. The total time is 16*tx.
        ty (float): The time in seconds to spend in the +/-Y frame in each instance. The total time is 16*ty. Defaults to None, in which case tx is used.
        tz (float): The time in seconds to spend in the +/-Z frame in each instance. The total time is 16*tz. Defaults to None, in which case tx is used.

    Returns:
        np.ndarray: The frame matrix.
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


def DROID_C3PO(t):
    """
    Generates the frame matrix for the DROID-C3PO sequence as described in arXiv:2305.09757v1 (2023).

    Args:
        t (float): The time in seconds to spend in each frame.
    """

    def x(t=0):
        return np.array([1, 0, 0, 0, 0, 0, t])

    def y(t=0):
        return np.array([0, 1, 0, 0, 0, 0, t])

    def z(t=0):
        return np.array([0, 0, 1, 0, 0, 0, t])

    def mx(t=0):
        return np.array([-1, 0, 0, 0, 0, 0, t])

    def my(t=0):
        return np.array([0, -1, 0, 0, 0, 0, t])

    def mz(t=0):
        return np.array([0, 0, -1, 0, 0, 0, t])

    def xt(t=0):
        return np.array([0, 0, 0, 1, 0, 0, t])

    def yt(t=0):
        return np.array([0, 0, 0, 0, 1, 0, t])

    def zt(t=0):
        return np.array([0, 0, 0, 0, 0, 1, t])

    def mxt(t=0):
        return np.array([0, 0, 0, -1, 0, 0, t])

    def myt(t=0):
        return np.array([0, 0, 0, 0, -1, 0, t])

    def mzt(t=0):
        return np.array([0, 0, 0, 0, 0, -1, t])

    frame_matrix = np.array(
        [
            z(t),  # 0
            my(),
            mz(t),
            y(),
            mx(t),
            z(),
            x(t),
            mz(),
            my(t),
            x(),
            y(t),  # 5
            mx(),
            zt(t),
            myt(),
            mzt(t),
            yt(),
            xt(t),
            zt(),
            mxt(t),
            mzt(),
            myt(t),  # 10
            mxt(),
            yt(t),
            xt(),
            mz(t),
            y(),
            z(t),
            my(),
            mx(t),
            mz(),
            x(t),  # 15
            z(),
            y(t),
            mx(),
            my(t),
            x(),
            mzt(t),
            yt(),
            zt(t),
            myt(),
            xt(t),  # 20
            mzt(),
            mxt(t),
            zt(),
            yt(t),
            xt(),
            myt(t),
            mxt(),
            mz(t),
            my(),
            z(t),  # 25
            y(),
            x(t),
            z(),
            mx(t),
            mz(),
            y(t),
            x(),
            my(t),
            mx(),
            mzt(t),  # 30
            myt(),
            zt(t),
            yt(),
            mxt(t),
            zt(),
            xt(t),
            mzt(),
            yt(t),
            mxt(0),
            myt(t),  # 35
            xt(),
            z(t),
            y(),
            mz(t),
            my(),
            x(t),
            mz(),
            mx(t),
            z(),
            my(t),  # 40
            mx(),
            y(t),
            x(),
            zt(t),
            yt(),
            mzt(t),
            myt(),
            mxt(t),
            mzt(),
            xt(t),  # 45
            zt(),
            myt(t),
            xt(),
            yt(t),
            mxt(),
            myt(t),
            mxt(),
            yt(t),
            mzt(),
            mxt(t),  # 50
            zt(),
            xt(t),
            yt(),
            zt(t),
            myt(),
            mzt(t),
            mx(),
            my(t),
            x(),
            y(t),  # 55
            mz(),
            x(t),
            z(),
            mx(t),
            y(),
            z(t),
            my(),
            mz(t),
            mxt(),
            yt(t),  # 60
            xt(),
            myt(t),
            zt(),
            mxt(t),
            mzt(),
            xt(t),
            myt(),
            mzt(t),
            yt(),
            zt(t),  # 65
            x(),
            y(t),
            mx(),
            my(t),
            z(),
            x(t),
            mz(),
            mx(t),
            my(),
            mz(t),  # 70
            y(),
            z(t),
            xt(),
            yt(t),
            mxt(),
            myt(t),
            mzt(),
            xt(t),
            zt(),
            mxt(t),  # 75
            yt(),
            mzt(t),
            myt(),
            mzt(t),
            mx(),
            y(t),
            x(),
            my(t),
            mz(),
            mx(t),  # 80
            z(),
            x(t),
            y(),
            mz(t),
            my(),
            z(t),
            mxt(),
            myt(t),
            xt(),
            yt(t),  # 85
            zt(),
            xt(t),
            mzt(),
            mxt(t),
            myt(),
            zt(t),
            yt(),
            mzt(t),
            x(),
            my(t),  # 90
            mx(),
            y(t),
            z(),
            mx(t),
            mz(),
            x(t),
            my(),
            z(t),
            y(),
            mz(t),  # 95
            xt(),
        ]
    ).T
    return frame_matrix


def XY8(tx, ty, tz):
    frame_matrix = np.array(
        [
            [0, 0, 1, tz],
            [0, 1, 0, ty],
            [0, 0, -1, tz],
            [-1, 0, 0, tx],
            [0, 0, 1, tz],
            [0, -1, 0, ty],
            [0, 0, -1, tz],
            [1, 0, 0, tx],
            [0, 0, 1, tz],
            [-1, 0, 0, tx],
            [0, 0, -1, tz],
            [0, 1, 0, ty],
            [0, 0, 1, tz],
            [1, 0, 0, tx],
            [0, 0, -1, tz],
            [0, -1, 0, ty],
        ]
    ).T

    return frame_matrix

# TODO: This is wrong, fix referring to MACE repo
def pulses_to_frame_matrix(pulses):
    """
    Converts a list of pulses to a toggling frame matrix.

    Args:
        pulses (list): The list of pulses.

    Returns:
        np.ndarray: The frame matrix where each column corresponds to a frame. The first three rows correspond to the orientation of the original +Sz operator along the +X, +Y, +Z axes. Each column should have +/- 1 in one entry and zero in the others. The fourth row is the duration of that frame.
    """
    sz = np.array([0, 0, 1])
    frames = []

    if isinstance(pulses[0], Wait):
        frames.append([sz[0], sz[1], sz[2], pulses[0].duration])
        pulses = pulses[1:]

    # split pi pulses into two pi/2 pulses
    for pulse in pulses:
        if isinstance(pulse, AreaPulse) and np.isclose(pulse.pulse_area, np.pi):
            sz = R.from_rotvec(np.pi/2 * np.array([np.cos(float(pulse.phase)), np.sin(float(pulse.phase)), 0])).apply(sz)
            frames.append([sz[0], sz[1], sz[2], 0])
            sz = R.from_rotvec(np.pi/2 * np.array([np.cos(float(pulse.phase)), np.sin(float(pulse.phase)), 0])).apply(sz)
            frames.append([sz[0], sz[1], sz[2], 0])
        elif isinstance(pulse, AreaPulse) and np.isclose(pulse.pulse_area, np.pi/2):
            sz = R.from_rotvec(pulse.pulse_area * np.array([np.cos(float(pulse.phase)), np.sin(float(pulse.phase)), 0])).apply(sz)
            frames.append([sz[0], sz[1], sz[2], 0])
        elif isinstance(pulse, Wait):
            frames[-1][-1] += pulse.duration

    frames = np.array(frames).T

    # round directions to +/-1
    frames[:3] = np.round(frames[:3])

    return frames

def TAT_experiment(tXY8, nXY8s):
    pulses = [
        # PiOver2Pulse(phase=0),
        Wait(tXY8 / 12),
        PiPulse(phase=-np.pi / 2),
        Wait(tXY8 / 12),
        PiOver2Pulse(phase=0),
        Wait(tXY8 / 12),
        PiOver2Pulse(phase=0),
        Wait(tXY8 / 12),
        PiPulse(phase=-np.pi / 2),
        Wait(tXY8 / 12),
        PiOver2Pulse(phase=0),
        Wait(tXY8 / 12),
        PiOver2Pulse(phase=0),
        Wait(tXY8 / 12),
        PiOver2Pulse(phase=0),
        Wait(tXY8 / 12),
        PiOver2Pulse(phase=0),
        Wait(tXY8 / 12),
        PiPulse(phase=-np.pi / 2),
        Wait(tXY8 / 12),
        PiOver2Pulse(phase=0),
        Wait(tXY8 / 12),
        PiOver2Pulse(phase=0),
        Wait(tXY8 / 12),
        PiPulse(phase=-np.pi / 2),
    ]
    if nXY8s == 1:
        return pulses
    else:
        return deepcopy(pulses) + sum([deepcopy(pulses[1:]) for i in range(1, nXY8s)], [])
    

def randomized_benchmarking(l):
    """
    Generates a randomized benchmarking sequence of length l as described in https://journals.aps.org/pra/abstract/10.1103/PhysRevA.77.012307.

    The sequence consists of alternating pi and pi/2 pulses. The pi pulses are chosen to be about the +/-X, +/-Y, and +/-Z axes and no operation with equal probability. Pulses about the Z axis are realized by changing the phase of subsequent pulses.
    
    The pi/2 pulses are chosen to be about the +/-X and +/-Y axes with equal probability.
    
    The sequence contains l pi/2 pulses, not counting the final pi/2 pulse to rotate the final state back to the +/-Z axis.

    Args:
        l (int): The length of the sequence.

    Returns:
        list: A list of pulses.
        final_dir (int): +/-1, corresponding to the direction of the final state along the Z axis.
    """

    pi_over_2_pulses = [
        PiOver2Pulse(phase=0),
        PiOver2Pulse(phase=np.pi / 2),
        PiOver2Pulse(phase=np.pi),
        PiOver2Pulse(phase=3 * np.pi / 2),
    ]

    pulses = []
    phase = 0
    for i in range(l + 1):
        # Random pi pulse
        pi_axis = np.random.randint(4)
        pi_sign = np.random.randint(2)
        if pi_axis == 2:
            pass
        elif pi_axis == 3:
            phase += np.pi
        else:
            pulses.append(PiPulse(phase=phase + pi_axis * np.pi / 2 + pi_sign * np.pi))

        pulses.append(Wait(1e-6))

        # end with a pi pulse
        if i == l:
            break
        
        # Random pi/2 pulse
        pulses.append(pi_over_2_pulses[np.random.randint(4)])

        pulses.append(Wait(1e-6))

    # Determine the state after the sequence
    state = np.array([0, 0, 1])
    for pulse in pulses:
        if isinstance(pulse, AreaPulse):
            r = R.from_rotvec(pulse.pulse_area * np.array([np.cos(float(pulse.phase)), np.sin(float(pulse.phase)), 0]))
            state = r.apply(state)

    # Check which pi/2 pulse, if any, is needed to rotate the state back to the +/-Z axis
    final_dir = np.random.randint(2) * 2 - 1
    final_state = [0, 0, final_dir]
    final_pulses = pi_over_2_pulses + [PiPulse(phase=0)]
    for pulse in final_pulses:
        if isinstance(pulse, AreaPulse):
            r = R.from_rotvec(pulse.pulse_area * np.array([np.cos(float(pulse.phase)), np.sin(float(pulse.phase)), 0]))
            if np.allclose(r.apply(state), final_state):
                pulses.append(pulse)
                break
    
    return pulses, final_dir

# if __name__ == "__main__":
#     for i in range(10):
#         pulses, final_dir = randomized_benchmarking(20)
#         display_pulses(pulses)


# if __name__ == "__main__":
#     frame_matrix = DROID_C3PO(0.1)
#     display_frame_matrix(frame_matrix)
# frame_matrix = DROID_R2D2(0.1)
# display_frame_matrix(frame_matrix)
# pulses = frame_matrix_to_pulses(frame_matrix)

# import synthesizer_sequences as ss

# sequence = {
#     0: [
#         ss.SetTransition(ss.Transition(1, [1], [1])),
#     ]
#     + pulses,
# }
# compiled, durations = ss.compile_sequence(sequence, True)

# # save compiled sequence to json file
# import json

# with open("DROID_R2D2.json", "w") as outfile:
#     json.dump(json.loads(compiled), outfile)


# if __name__ == "__main__":
    # print("Optimal 6 tau")
    # frame_matrix = opt_6tau(100e-6)
    # validate_frame_matrix(frame_matrix)
    # print(check_decoupling(frame_matrix, np.pi / 4 * 10e-6))
    # print("DROID-2D2")
    # frame_matrix = DROID_R2D2(100e-6)
    # validate_frame_matrix(frame_matrix)
    # print(check_decoupling(frame_matrix, 10e-6))

    # print("XY8")
    # frame_matrix = TAT_experiment(100e-6, 1)
    # frame_matrix = XY8(1, 0, 1)
    # frame_matrix[:3, :] = np.roll(frame_matrix[:3, :], -1, axis=0)
    # frame_matrix = np.concatenate([
    #     frame_matrix,
    #     frame_matrix[:, :-1],
    #     np.array([[0, 0, 1, 0]]).T
    # ], axis=1)
    # validate_frame_matrix(frame_matrix)
    # for k, v in check_decoupling(frame_matrix, 10e-6).items():
    #     print(k, ":", v)
    # print(display_frame_matrix(frame_matrix))
    # pulses = frame_matrix_to_pulses(frame_matrix)
    # display_pulses(pulses)

    # display_pulses(TAT_experiment(100e-6, 2))

if __name__ == "__main__":
    pulses = TAT_experiment(100e-6, 1)
    frame_matrix = pulses_to_frame_matrix(pulses)
    print(frame_matrix.T)
    display_frame_matrix(frame_matrix)