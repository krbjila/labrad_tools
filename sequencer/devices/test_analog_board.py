import unittest
from unittest.mock import PropertyMock
import json

from pathlib import Path
import sys
sys.path.append([str(i) for i in Path(__file__).parents if str(i).endswith("labrad_tools")][0])

from analog_board import * 

class TestAnalogBoard(unittest.TestCase):
    def setUp(self):
        config = {
            "device_type": "AnalogBoard",
            "connection_type": "OKFPGA",
            "servername": "test_okfpga",
            "address": "KRbAnlgTest",
            "bitfile": "KRbAnlgNew.bit",
            "clk": 526315.7894736842,
            "channels": [
                {
                    "loc": 0, 
                    "name": "DAC0", 
                    "mode": "auto", 
                    "manual_output": 10.0
                },
                {
                    "loc": 1, 
                    "name": "DAC1", 
                    "mode": "auto", 
                    "manual_output": 10.0
                }
            ]
        }

        p = PropertyMock(return_value = "test")
        AnalogBoard.name = p
        self.board = AnalogBoard(config)

    def test_duplicates(self):
        seq = {
            "DAC0@test00": [{'dt': 10e-3, 'type': 's', 'vf': 1}, {'dt': 10e-3, 'type': 's', 'vf': 1}],
            "DAC1@test01": [{'dt': 10e-3, 'type': 's', 'vf': 0}]
        }
        ramps = self.board.make_sequence_ramps(seq)
        self.assertEqual(len(ramps), 3)


if __name__ == '__main__':
    unittest.main()