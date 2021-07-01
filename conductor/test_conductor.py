
'''
Run me with sequencer/test_server.py to run the Sequencer server 
without connections to FPGAs.

The FPGA connections are mocked up in the TestOkfpga class
(all methods just pass)
'''
import os
from conductor import ConductorServer

if __name__ == "__main__":
    from labrad import util
    path = os.path.dirname(os.path.abspath(__file__))
    util.runServer(ConductorServer(path + '/test_config.json'))
