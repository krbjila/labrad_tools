import labrad
import json
import numpy as np

class STIRAP_DDS(object):
    def __init__(self, config={}):
        cxn = labrad.connect()
        self.server = cxn.servers['krbg2_ad9910']
        self.dt = 1000
        self.nsteps = 5000
        self.default_freq = 130
        profiles = [{'profile':i,'freq':10, 'ampl': 0, 'phase':0} for i in range(8)]
        self.profiles = json.dumps(profiles)

    # def _check_program_params(self, value):
    #     if(value['program'][0]['mode'] != 'sweep'):
    #         raise Exception('Please only use sweep mode')
    #     if(value['program'][0]['dt'] < self.dt):
    #         value['program'][0]['dt'] = self.dt
    #         print('Sweep time too short. Replaced with default 1s')
    #     if(value['program'][0]['nsteps'] < self.nsteps):
    #         value['program'][0]['nsteps'] = self.nsteps
    #         print('Too few sweep steps. Replaced with default 5000 steps')

    def _program_from_freqs(self, freqs):
        program = [{"mode": "sweep", "start":self.default_freq, "stop":freqs[0], "dt":self.dt, "nsteps": self.nsteps}]
        for i in range(len(freqs)-1):
            program.append({"mode": "sweep", "start":freqs[i], "stop":freqs[i+1], "dt":self.dt, "nsteps": self.nsteps})
        # print(program)
        program.append({"mode": "sweep", "start":freqs[-1], "stop":self.default_freq, "dt":self.dt, "nsteps": self.nsteps})
        return json.dumps(program)

    def update(self,freqs, device):
        #update device
        program = self._program_from_freqs(freqs)
        s = self.server.select_device(device)
        self.server.write_data(program, self.profiles)
        self.server.force_trigger()
        print('program written')

if __name__ == '__main__':
    device = 'stirap_ch1'
    freqs = [180,200,220]
    dds = STIRAP_DDS()
    dds.update(freqs,device)

    

