import sys
import numpy as np
sys.path.append('../')
from generic_device.generic_parameter import GenericParameter

from twisted.internet.defer import inlineCallbacks, Deferred
from twisted.internet.reactor import callLater
from labrad.wrappers import connectAsync

from conductor_device.conductor_parameter import ConductorParameter

class Blackman(ConductorParameter):
    """
    Blackman(ConductorParameter)

    Conductor parameter that configures the function generator to output a `Blackman window <https://en.wikipedia.org/wiki/Window_function#Blackman_window>`_.

    The duration (in s) and peak amplitude (in V) of the window function can be configured. Example config:

    .. code-block:: json

        {
            "pulseShaperAWG": {
                "blackman": {
                    "period": 150E-6,
                    "amplitude": 0.5
                }
            }
        }
    """
    priority = 1

    def __init__(self, config={}):
        super(Blackman, self).__init__(config)
        self.value = {"amplitude": self.default_amplitude, "period": self.default_period}

    @inlineCallbacks
    def initialize(self):
        self.cxn = yield connectAsync()
        self.usb = self.cxn.polarkrb_usb
        address = 'USB0::0x0957::0x0407::MY44005958::INSTR'
        try:
            # Build Blackman waveform
            def blackman(tau, t):
	            return (0.42 - 0.5*np.cos(2*np.pi*t/tau) + 0.08 * np.cos(4*np.pi*t/tau))

            samples = 8192
            pts = np.array(blackman(samples,np.arange(samples)))*(samples-1)
            pts = pts.astype(int)
            waveform = ''
            for x in pts:
                waveform += str(x) + ','
            waveform = waveform[:-1]

            yield self.usb.select_interface(address)
            yield self.usb.write('DATA:DAC VOLATILE,' + waveform)

            yield self.usb.write('DATA:COPY BLACKMAN')

            yield self.usb.write('OUTP OFF')
            yield self.usb.write('FUNC:USER BLACKMAN')

            yield self.usb.write('FREQ {} Hz'.format(1.0/self.value['period']))
            yield self.usb.write('VOLT {} VPP'.format(self.value['amplitude']))
            yield self.usb.write('VOLT:OFFS 0 V')

            yield self.usb.write('BURS:MODE TRIG')
            yield self.usb.write('BURS:NCYC 1')
            yield self.usb.write('TRIG:SOUR EXT')

            yield self.usb.write('OUTP ON')
        except Exception as e:
            print("Could not connect to pulse shaping AWG: {}".format(e))

    @inlineCallbacks
    def update(self):
        if self.value:
            try:
                yield self.usb.write('FREQ {} Hz'.format(1.0/self.value['period']))
                yield self.usb.write('VOLT {} VPP'.format(self.value['amplitude']))
                yield self.usb.write('OUTP ON')
            except Exception as e:
                print("Could not update pulse shaping AWG: {}".format(e))
