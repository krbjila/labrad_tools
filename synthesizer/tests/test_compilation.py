import unittest
import synthesizer_sequences_base as ssb
from synthesizer_compiler import *


class TestCompilation(unittest.TestCase):
    def test_compilation(self):
        subsubroutine = ssb.Subroutine(
            ssb.Sequence(
                ssb.Timestamp(1, {"RF0": ssb.RFUpdate(1e6)}),
                ssb.Timestamp(1, {"RF0": ssb.RFUpdate(2e6)}),
            )
        )
        subroutine = ssb.Subroutine(
            ssb.Sequence(
                subsubroutine,
                ssb.Timestamp(1, {"RF0": ssb.RFUpdate(1e6)}),
                ssb.Timestamp(1, {"RF0": ssb.RFUpdate(2e6)}),
            )
        )
        sequence = ssb.Sequence(
            ssb.Repeat(subsubroutine, 10),
            subroutine,
            subsubroutine,
            ssb.Repeat(
                ssb.Sequence(
                    subroutine,
                    ssb.Timestamp(1, {"RF0": ssb.RFUpdate(1e6)}),
                    ssb.Timestamp(1, {"RF0": ssb.RFUpdate(2e6)}),
                ),
                3,
            ),
        )
        generate_instructions(sequence)


if __name__ == "__main__":
    unittest.main()
