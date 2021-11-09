"""
TODO: 


..
    ### BEGIN NODE INFO
    [info]
    name = stirap
    version = 1.1
    description = 
    instancename = %LABRADNODE%_stirap

    [startup]
    cmdline = %PYTHON% %FILE%
    timeout = 20

    [shutdown]
    message = 987654321
    timeout = 20
    ### END NODE INFO
"""

from labrad.server import LabradServer, setting
from twisted.internet.defer import inlineCallbacks

import json


class StirapServer(LabradServer):
    """
    TODO:
    Server for communicating with AD9910 + Arduino setup.

    The current hardware setup uses an Arduino to program the AD9910 evaluation board over SPI.
    The AD9910 has a set of 8 single-frequency registers (called the "profiles") that can be rapidly and phase-coherently switched via external digital inputs.
    Additionally, the Arduino can hold an array (length < 12) of values (called the "program"), which are advanced by an external trigger input to the Arduino.
    The program also allows for frequency sweeps, which are useful for performing adiabatic rapid passages (ARPs).
    
    Currently, this server assumes this general architecture; however, it should be straightforward to add new hardware implementations (``./devices``) in the future.
    """
    name = '%LABRADNODE%_stirap'
    default_up_freq = 74
    default_down_freq = 130
    dt = 1000
    nsteps = 5000
    servername = 'krbg2_ad9910'

    channels = {"up" : {"channel" : "stirap_ch1", "last_freq": default_up_freq}, 
                "down" : {"channel" : "stirap_ch2", "last_freq": default_down_freq}}

    profiles = json.dumps([{'profile':i,'freq':10, 'ampl': 0, 'phase':0} for i in range(8)])
        
    def initServer(self):
        self.connect()

    @inlineCallbacks
    def connect(self):
        self.server = yield self.client.servers[self.servername]
    
    def _program_from_freqs(self, channel, freqs):
        program = [{"mode": "sweep", "start": self.channels[channel]['last_freq'], "stop":freqs[0], "dt":self.dt, "nsteps": self.nsteps}]
        for i in range(len(freqs)-1):
            program.append({"mode": "sweep", "start":freqs[i], "stop":freqs[i+1], "dt":self.dt, "nsteps": self.nsteps})
        # print(program)
        for _ in range(len(freqs), 11):
            program.append({"mode": "single", "freq" : freqs[-1], "ampl": 0, "phase": 0})
        return json.dumps(program)
    
    @setting(10, "Set EOM Freqs", channel='s', freqs='*v')
    def set_eom_freqs(self, c, channel, freqs):
        """
        set_eom_freqs(self, c, channel, freqs)

        TODO:

        Args:
            c: LabRAD context
            channel (str): dds channel name (either "up" or "down") 
            freqs ([float]): list of frequencies to set 
        Returns:

        """
        try:
            program = self._program_from_freqs(channel,freqs)
            self.channels[channel]['last_freq'] = freqs[-1]
            self.server.select_device(self.channels[channel]['channel'])
            self.server.write_data(program, self.profiles)
            self.server.force_trigger()

        except KeyError:
            print('Please select a valid device: {}\n'.format(self.channels.keys()))
        
        except IndexError:
            print('Freqs list was empty\n')
        


if __name__ == '__main__':
    from labrad import util
    util.runServer(StirapServer())
