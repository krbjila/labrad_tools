from andor.proxy import AndorProxy

from twisted.internet.defer import inlineCallbacks
from labrad.wrappers import connectAsync

from conductor_device.conductor_parameter import ConductorParameter

from traceback import print_exc

import numpy as np

class AndorDevice(ConductorParameter):
    """
    Conductor parameter for controlling Andor cameras. Individual cameras should subclass this. The configuration for which hardware a conductor parameter communicates with is set in :mod:`conductor.conductor`'s `config.json <https://github.com/krbjila/labrad_tools/blob/master/conductor/config.json>`_.
    Data format:::
        [...]
    """
    priority = 1
    value_type = 'single'

    def __init__(self, server_name, serial, config={}):
        super(AndorDevice, self).__init__(config)
        self.serial = serial
        self.server_name = server_name
        self.value = None

        if "temperature" not in config:
            self.temperature = -20

    @inlineCallbacks
    def initialize(self):
        self.cxn = yield connectAsync()
        self.server = self.cxn[self.server_name]
        self.andor = AndorProxy(self.server)

        cameras = self.andor.get_interface_list()
        if self.serial not in cameras:
            raise Exception('Camera {} not found'.format(self.serial))
        self.andor.select_interface(self.serial)

        self.andor.SetTemperature(self.temperature)
        self.andor.SetFanMode(2)
        self.andor.SetCoolerMode(0) # Returns to ambient temperature on shutdown
        self.andor.CoolerON()

        self.andor.SetReadMode(4) # Image
        self.andor.SetEMGainMode(3) # Real EM Gain
        self.andor.SetEMAdvanced(0)
        self.andor.SetTriggerMode(1) # External
        self.andor.SetFastExtTrigger(1)

        self.andor.SetNumberAccumulations(1)


    @inlineCallbacks
    def update(self):
        if self.value and self.value['takeImage']:
            try:
                # TODO: save a placeholder image gracefully, if the camera was acquiring
                self.andor.AbortAcquisition()
                
                # Configure the camera
                acqLength = self.value['acqLength']
                adChannel = self.value['adChannel']
                dx = self.value['dx']
                dy = self.value['dy']
                binning = self.value['binning']
                emEnable = self.value['emEnable']
                emGain = self.value['emGain']
                expTime = self.value['expTime']
                hss = self.value['hss']
                kinFrames = self.value['kinFrames']
                preAmpGain = self.value['preAmpGain']
                vss = self.value['vss']
                xOffset = self.value['xOffset']
                yOffset = self.value['yOffset']
                temperature = self.value['temperature']

                if float(self.andor.GetTemperature()) > 0:
                    print("Cooler restart.")
                    self.andor.SetFanMode(2) # 2 for off
                    self.andor.SetTemperature(temperature)
                    self.andor.SetCoolerMode(0) # 1 Returns to ambient temperature on shutdown
                    self.andor.CoolerON()


                if emEnable:
                    self.andor.SetOutputAmplifier(0)
                    self.andor.SetEMCCDGain(emGain)
                    self.andor.SetHSSpeed(0, hss)
                else:
                    self.andor.SetOutputAmplifier(1)
                    self.andor.SetHSSpeed(1, hss)

                self.andor.SetADChannel(adChannel)
                self.andor.SetPreAmpGain(preAmpGain)

                if binning:
                    bin = 2
                else:  
                    bin = 1

                if kinFrames > 1:
                    self.andor.SetAcquisitionMode(4) # Fast Kinetics
                    self.andor.SetFKVShiftSpeed(vss)
                    self.andor.SetFastKineticsEx(dy, kinFrames, expTime, 4, bin, bin, yOffset)
                else:
                    self.andor.SetAcquisitionMode(3) # Kinetics
                    self.andor.SetNumberKinetics(acqLength)
                    self.andor.SetVSSpeed(vss)
                    self.andor.SetExposureTime(expTime)
                    self.andor.SetImage(bin, bin, xOffset + 1, dx + xOffset, yOffset + 1, dy + yOffset)

                if acqLength == 1:
                    timeouts = [60E3] # ms
                else:
                    timeouts = [60E3] + [4E3] * (acqLength - 1) # ms

                self.andor.SetShutter(1, 1, 0, 0) # Open the shutter
                
                if kinFrames > 1 and acqLength > 1:
                    for i in range(acqLength):
                        self.andor.StartAcquisition()
                        # TODO: Handle timeouts gracefully
                        self.andor.WaitForAcquisitionTimeOut(timeouts[i])
                else:
                    self.andor.StartAcquisition()
                    self.andor.WaitForAcquisitionTimeOut(timeouts[0])

                self.andor.SetShutter(1, 2, 0, 0) # Close the shutter
                
                first, last = self.andor.GetNumberNewImages()
                data, validfirst, validlast = self.andor.GetImages(first, last, acqLength*dx*dy)

                np.savez_compressed("poo.npz", data.reshape(acqLength, dy, dx))
            except Exception as e:
                print_exc(e)