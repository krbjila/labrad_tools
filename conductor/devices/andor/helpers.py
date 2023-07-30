import os, sys
sys.path.append("/home/bialkali/labrad_tools/andor")

from proxy import AndorProxy

from twisted.internet.defer import inlineCallbacks
from labrad.wrappers import connectAsync

from conductor_device.conductor_parameter import ConductorParameter

from traceback import print_exc

import numpy as np


#### TODO ####
# Save images in the correct location (data/year/month/day/location/prefix_shotnumber.npz). Should save images to a temporary location, then copy them to the dataserver using a new process, so the conductor doesn't hang.
# Make sure the image format is the same as the previous version.
# Add metadata to the image, including the dictionary of conductor parameters.
# Gracefully handle timeouts.
# What happens if one of the configuration commands fails?
# What happens if the acquisition isn't finished when the parameter is updated? Should save a placeholder image.


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

        cameras = yield self.andor.get_interface_list()
        print("fart! poo!")
        print(cameras)
        if self.serial not in cameras:
            raise Exception('Camera {} not found'.format(self.serial))
        yield self.andor.select_interface(self.serial)

        yield self.andor.SetTemperature(self.temperature)
        yield self.andor.SetFanMode(2)
        yield self.andor.SetCoolerMode(0) # Returns to ambient temperature on shutdown
        yield self.andor.CoolerON()

        yield self.andor.SetReadMode(4) # Image
        yield self.andor.SetEMGainMode(3) # Real EM Gain
        yield self.andor.SetEMAdvanced(0)
        yield self.andor.SetTriggerMode(1) # External
        yield self.andor.SetFastExtTrigger(1)

        yield self.andor.SetNumberAccumulations(1)


    @inlineCallbacks
    def update(self):
        if self.value and self.value['takeImage']:
            try:
                # TODO: save a placeholder image gracefully, if the camera was acquiring
                yield self.andor.AbortAcquisition()
                
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

                current_temp = yield self.andor.GetTemperature()
                if float(current_temp) > 0:
                    print("Cooler restart.")
                    yield self.andor.SetFanMode(2) # 2 for off
                    yield self.andor.SetTemperature(temperature)
                    yield self.andor.SetCoolerMode(0) # 1 Returns to ambient temperature on shutdown
                    yield self.andor.CoolerON()


                if emEnable:
                    yield self.andor.SetOutputAmplifier(0)
                    yield self.andor.SetEMCCDGain(emGain)
                    yield self.andor.SetHSSpeed(0, hss)
                else:
                    yield self.andor.SetOutputAmplifier(1)
                    yield self.andor.SetHSSpeed(1, hss)

                yield self.andor.SetADChannel(adChannel)
                yield self.andor.SetPreAmpGain(preAmpGain)

                if binning:
                    bin = 2
                else:  
                    bin = 1

                if kinFrames > 1:
                    yield self.andor.SetAcquisitionMode(4) # Fast Kinetics
                    yield self.andor.SetFKVShiftSpeed(vss)
                    yield self.andor.SetFastKineticsEx(dy, kinFrames, expTime, 4, bin, bin, yOffset)
                else:
                    yield self.andor.SetAcquisitionMode(3) # Kinetics
                    yield self.andor.SetNumberKinetics(acqLength)
                    yield self.andor.SetVSSpeed(vss)
                    yield self.andor.SetExposureTime(expTime)
                    yield self.andor.SetImage(bin, bin, xOffset + 1, dx + xOffset, yOffset + 1, dy + yOffset)

                if acqLength == 1:
                    timeouts = [60E3] # ms
                else:
                    timeouts = [60E3] + [4E3] * (acqLength - 1) # ms

                self.andor.SetShutter(1, 1, 0, 0) # Open the shutter
                
                if kinFrames > 1 and acqLength > 1:
                    for i in range(acqLength):
                        yield self.andor.StartAcquisition()
                        # TODO: Handle timeouts gracefully
                        yield self.andor.WaitForAcquisitionTimeOut(timeouts[i])
                else:
                    yield self.andor.StartAcquisition()
                    yield self.andor.WaitForAcquisitionTimeOut(timeouts[0])

                yield self.andor.SetShutter(1, 2, 0, 0) # Close the shutter
                
                first, last = yield self.andor.GetNumberNewImages()
                data, validfirst, validlast = yield self.andor.GetImages(first, last, acqLength*dx*dy)

                np.savez_compressed("poo.npz", data.reshape(acqLength, dy, dx))
            except Exception as e:
                print_exc(e)