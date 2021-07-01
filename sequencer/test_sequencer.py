'''
Run me with okfpga/test/test_server.py to run the Sequencer server 
without connections to FPGAs.

The FPGA connections are mocked up in the TestOkfpga class
(all methods just pass)
'''
from sequencer import SequencerServer

if __name__ == "__main__":
    from labrad import util
    util.runServer(SequencerServer('./test_config.json'))
