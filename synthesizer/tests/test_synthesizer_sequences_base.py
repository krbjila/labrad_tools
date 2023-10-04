import unittest

from synthesizer.synthesizer_sequences_base import *


class TestSequence(unittest.TestCase):
    def test_duration(self):
        sequence = Sequence(Timestamp(1), Timestamp(2))
        self.assertEqual(sequence.duration, 3)

        # TODO: Parallel sequences are not yet implemented
        # sequence = Parallel(Timestamp(1), Timestamp(2))
        # self.assertEqual(sequence.duration, 2)

        sequence = Timestamp(1) * 3
        self.assertEqual(sequence.duration, 3)

        sequence = 3 * Timestamp(1) + Timestamp(2)

    def test_channels(self):
        sequence = Sequence(Timestamp(1, {"RF0": RFUpdate()}))
        self.assertEqual(sequence.channels, {"RF0"})

        sequence = Sequence(
            Timestamp(1, {"RF0": RFUpdate()}), Timestamp(2, {"RF1": RFUpdate()})
        )
        self.assertEqual(sequence.channels, {"RF0", "RF1"})

        # TODO: Parallel sequences are not yet implemented
        # sequence = Parallel(
        #     Timestamp(1, {"RF0": RFUpdate()}), Timestamp(2, {"RF1": RFUpdate()})
        # )
        # self.assertEqual(sequence.channels, {"RF0", "RF1"})

        sequence = Repeat(Timestamp(1, {"RF0": RFUpdate()}), 3)
        self.assertEqual(sequence.channels, {"RF0"})

    def test_addition(self):
        sequence = Timestamp(1) + Timestamp(2)
        self.assertEqual(sequence.duration, 3)

        sequence = Sequence(Timestamp(1), Timestamp(2)) + Timestamp(3)
        self.assertEqual(sequence.duration, 6)

    def test_multiplication(self):
        sequence = Timestamp(1) * 3
        self.assertEqual(sequence.duration, 3)

        sequence = 3 * Timestamp(1)
        self.assertEqual(sequence.duration, 3)

        sequence = Sequence(Timestamp(1), Timestamp(2)) * 3
        self.assertEqual(sequence.duration, 9)
        sequence *= 3
        self.assertEqual(sequence.duration, 27)
        self.assertEqual(sequence.times, 9)

    def test_compilation(self):
        sequence = Sequence(Timestamp(1), Timestamp(2))
        self.assertEqual(sequence.compile(set()), Sequence(Timestamp(3)))

        sequence = Sequence(Sequence(Timestamp(1)), Timestamp(2))
        self.assertEqual(sequence.compile(set()), Sequence(Timestamp(3)))

        sequence = Sequence(Sequence(Timestamp(1)), Sequence(Timestamp(2)))
        self.assertEqual(sequence.compile(set()), Sequence(Timestamp(3)))

        sequence = Sequence(Timestamp(1, {"RF0": RFUpdate()}))
        self.assertEqual(
            sequence.compile({"RF0"}), Sequence(Timestamp(1, {"RF0": RFUpdate()}))
        )

        # TODO: Compilation of parallel sequences is not yet implemented
        # sequence = Parallel(Timestamp(1), Timestamp(2))
        # compiled = sequence.compile(set())
        # for element in compiled.elements:
        #     self.assertEqual(element.duration, 2)

        sequence = Timestamp(1) * 3
        self.assertEqual(sequence.compile(set()), Timestamp(3))


if __name__ == "__main__":
    unittest.main()
