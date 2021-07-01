import os, sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from sequencer import SequencerServer

'''
Run me with okfpga/test/test_server.py to run the Sequencer server 
without connections to FPGAs.

The FPGA connections are mocked up in the TestOkfpga class
(all methods just pass)
'''
class TestSequencer(SequencerServer):
    def __init__(self):
        super(TestSequencer, self).__init__('./test_config.json')

def main():
    from labrad import util
    util.runServer(TestSequencer())

if __name__ == "__main__":
    main()
