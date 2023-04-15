import json
import numpy as np
import matplotlib.pyplot as plt
 
class evaporation():
 
    def __init__(self, trajpath = "./evap.json"):
        self.dt = 0.1 #Update freq with timestep [s]
        self.loadtraj(trajpath)
        self.trajgen()
 
    def loadtraj(self, path):
        if path is not None:
            with open("/home/bialkali/labrad_tools/magnetic_evaporation/evap.json", 'r') as infile:
                evap = json.load(infile)
 
            n = []
            for key, value in evap.items():
                setattr(self, key, value)
                if key in ['tau', 'amplitudes', 'start', 'stop', 'asymp']:
                    n.append(len(value))
            if not all( x == n[0] for x in n):
                raise Exception("All parameters must have the same length")
            else:
                self.nstep = n[0]
     
    def trajgen(self):
        F = np.array([])
        A = np.array([])
        for k in range(self.nstep):
            x = self.exponential(self.start[k],self.stop[k],self.asymp[k],self.tau[k])
            F = np.append(F,x)
            A = np.append(A,np.ones(len(x))*self.amplitudes[k])
        self.trajectory = F
        self.amps = A
        self.time = np.arange(len(F))*self.dt
        self.totaltime = max(self.time)
        self.points = len(self.time)
         
    def exponential(self,fi,fs,fa,tau):
        if fi <= fa or fs <= fa:
            raise Exception("Initial and final frequencies must be larger than asymptotic frequency")
         
        if fi > fs:
            tf = tau*np.log((float(fi)-fa)/(fs-fa))
            N = int(np.floor(tf/self.dt))
 
             
            Y = np.zeros(N)
            T = np.zeros(N)
            for k in range(int(N)):
                T[k] = k*self.dt
                Y[k] = (fi-fa)*np.exp(-T[k]/tau) + fa
            return Y
 
 
