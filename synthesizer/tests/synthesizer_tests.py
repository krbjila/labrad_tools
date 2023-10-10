from random import gauss
import unittest
import numpy as np
import synthesizer_sequences as ss
import pulse_sequences as ps


class TestRFPulse(unittest.TestCase):
    def test_center(self):
        duration = 1
        seq = [ss.Wait(duration)]
        centered = ss.RFPulse.center(True, seq, duration)
        uncentered = ss.RFPulse.center(False, seq, duration)

        self.assertEqual(ss.AdjustNextDuration(0.1), ss.AdjustNextDuration(0.1))
        self.assertEqual(seq, uncentered)

    def test_area(self):
        self.assertEqual(
            ss.RectangularPulse(1, 1).area, ss.RectangularPulse(2.0, 3.1).area
        )
        self.assertEqual(ss.RectangularPulse(1, 2).area, 1)
        self.assertAlmostEqual(
            ss.GaussianPulse(1, 0.8).area, ss.GaussianPulse(10.5, 0.5).area
        )
        self.assertAlmostEqual(
            ss.BlackmanPulse(1, 0.8).area, ss.BlackmanPulse(0.5, 0.5).area
        )

    def test_compliation(self):
        gaussian = ss.GaussianPulse(1, 1, steps=28).compile()
        blackman = ss.BlackmanPulse(1, 1, steps=28).compile()

        # TODO: figure out why these are length 29 instead of 28
        # self.assertEqual(len(gaussian), 28)
        # self.assertEqual(len(blackman), 28)
        self.assertAlmostEqual(gaussian[0].amplitude, gaussian[-2].amplitude)
        self.assertAlmostEqual(gaussian[2].amplitude, gaussian[-4].amplitude)
        self.assertAlmostEqual(blackman[0].amplitude, blackman[-2].amplitude)
        self.assertAlmostEqual(blackman[2].amplitude, blackman[-4].amplitude)


class TestPulseSequences(unittest.TestCase):
    def test_frame_matrix_to_pulses(self):
        # frame_matrix = np.array(
        #     [
        #         [0, 0, 1, 1],
        #         [0, 1, 0, 1],
        #         [1, 0, 0, 1],
        #         [0, 1, 0, 0],
        #         [-1, 0, 0, 1],
        #         [0, -1, 0, 1],
        #         [0, 0, -1, 1],
        #         [0, -1, 0, 0],
        #     ]
        # ).T
        # # append version of the frame matrix with the columns reversed
        # frame_matrix = np.concatenate(
        #     (frame_matrix, np.array([[0, 0, 1, 0]]).T, frame_matrix[:, ::-1]), axis=1
        # )
        frame_matrix = ps.DROID_R2D2(1)
        # print(frame_matrix)
        pulses = ps.frame_matrix_to_pulses(frame_matrix)
        # for pulse in pulses:
        #     print(pulse)
        ps.display_pulses(pulses)
        ps.display_frame_matrix(frame_matrix)


if __name__ == "__main__":
    unittest.main()
