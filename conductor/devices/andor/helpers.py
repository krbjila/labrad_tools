import os, sys
sys.path.append("/home/bialkali/labrad_tools/andor")

from proxy import AndorProxy

from twisted.internet.defer import inlineCallbacks
from labrad.wrappers import connectAsync

from conductor_device.conductor_parameter import ConductorParameter

from traceback import print_exc

import numpy as np
from datetime import datetime
import re
import multiprocessing as mp

#### TODO ####
# Save images in the correct location (data/year/month/day/location/prefix_shotnumber.npz). Should save images to a temporary location, then copy them to the dataserver using a new process, so the conductor doesn't hang.
# Make sure the image format is the same as the previous version.
# Add metadata to the image, including the dictionary of conductor parameters.
# What happens if one of the configuration commands fails?


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

    def save_data(self, frames):
        expected_frame_size = self.kinFrames * self.dy * self.dx / (self.bin * self.bin)
        if len(frames) < self.acqLength:
            print("Expected {} frames, got {}".format(self.acqLength, len(frames)))
            for i in range(self.acqLength - len(frames)):
                frames.append(np.zeros(expected_frame_size))
        data = np.array(frames).reshape((-1, self.dy/self.bin, self.dx/self.bin))

        if self.rotateImage:
            data = np.flip(np.swapaxes(np.array(data), 1, 2), axis=-1)

        savedir = "/dataserver/data/"+datetime.now().strftime("%Y/%m/%Y%m%d/")+self.saveFolder+"/"
        file_number = 0
        if not os.path.exists(savedir):
            os.makedirs(savedir)
        else:
            filelist = os.listdir(savedir)
            file_number = 0
            for f in filelist:
                match = re.match(self.filebase+"_([0-9])+.npz", f)
                if match and int(match.group(1)) > file_number:
                    file_number = int(match.group(1)) + 1

        path = savedir+self.filebase+"_"+str(file_number)

        metadata = {
            'camera': 'Andor iXon 888',
            'name': __class__ ,
            'serial': self.serial,
            'images': self.acqLength * self.kinFrames,
            'width': self.dx,
            'height': self.dy,
            'x_offset': self.xOffset,
            'y_offset': self.yOffset,
            'kinetics_frames': self.kinFrames,
            'exposure': self.expTime,
            'binning': (self.bin, self.bin),
            'timestamp': datetime.now(),
            'em_enable': 'on' if self.emEnable else 'off',
            'em_gain': self.emGain,
            'preamp_gain': self.preAmpGain,
            'vs_speed': self.vss,
            'shot': -1, # TODO: get shot number from logging server
            'path': path + ".npz",
            'id': None
        }

        # spawn a new process to save the data to prevent hanging
        p = mp.Process(target=self.save_data_process, args=(path, data, metadata))

    def save_data_process(self, path, data, metadata):
        # Define a temporary path to avoid conflicts when writing file
        # Otherwise, fitting program autoloads the file before writing is complete
        path_temp = path+"_temp.npz"
        with open(path_temp, 'wb') as f:
            np.savez_compressed(f, data=data, meta=metadata)
        os.rename(path_temp, path+".npz")

    @inlineCallbacks
    def update(self):
        if self.value and self.value['takeImage']:
            try:
                yield self.andor.AbortAcquisition()
                yield self.andor.CancelWait()
                
                # Configure the camera
                self.acqLength = self.value['acqLength']
                self.adChannel = self.value['adChannel']
                self.dx = self.value['dx']
                self.dy = self.value['dy']
                self.binning = self.value['binning']
                self.emEnable = self.value['emEnable']
                self.emGain = self.value['emGain']
                self.expTime = self.value['expTime']*1E-3 # ms to s
                self.hss = self.value['hss']
                self.kinFrames = self.value['kinFrames']
                self.preAmpGain = self.value['preAmpGain']
                self.vss = self.value['vss']
                self.xOffset = self.value['xOffset']
                self.yOffset = self.value['yOffset']
                self.temperature = self.value['temperature']
                self.saveFolder = self.value['saveFolder']
                self.filebase = self.value['filebase']
                self.rotateImage = self.value['rotateImage']

                current_temp = yield self.andor.GetTemperature()
                if float(current_temp) > 0:
                    print("Cooler restart.")
                    yield self.andor.SetFanMode(2) # 2 for off
                    yield self.andor.SetTemperature(self.temperature)
                    yield self.andor.SetCoolerMode(0) # 1 Returns to ambient temperature on shutdown
                    yield self.andor.CoolerON()


                if self.emEnable:
                    yield self.andor.SetOutputAmplifier(0)
                    yield self.andor.SetEMCCDGain(self.emGain)
                    yield self.andor.SetHSSpeed(0, self.hss)
                else:
                    yield self.andor.SetOutputAmplifier(1)
                    yield self.andor.SetHSSpeed(1, self.hss)

                yield self.andor.SetADChannel(self.adChannel)
                yield self.andor.SetPreAmpGain(self.preAmpGain)

                if self.binning:
                    self.bin = 2
                else:  
                    self.bin = 1

                if self.kinFrames > 1:
                    yield self.andor.SetAcquisitionMode(4) # Fast Kinetics
                    yield self.andor.SetFKVShiftSpeed(self.vss)
                    yield self.andor.SetFastKineticsEx(self.dy, self.kinFrames, self.expTime, 4, self.bin, self.bin, self.yOffset)
                else:
                    yield self.andor.SetAcquisitionMode(3) # Kinetics
                    yield self.andor.SetNumberKinetics(self.acqLength)
                    yield self.andor.SetVSSpeed(self.vss)
                    yield self.andor.SetExposureTime(self.expTime)
                    yield self.andor.SetImage(self.bin, self.bin, self.xOffset + 1, self.dx + self.xOffset, self.yOffset + 1, self.dy + self.yOffset)

                if self.acqLength == 1:
                    timeouts = [60E3] # ms
                else:
                    timeouts = [60E3] + [4E3] * (self.acqLength - 1) # ms

                self.andor.SetShutter(1, 1, 0, 0) # Open the shutter

                self.frames = []
                npixels = int(self.kinFrames * self.dx * self.dy / (self.bin * self.bin))

                if self.kinFrames > 1 and self.acqLength > 1:
                    for i in range(self.acqLength):
                        yield self.andor.StartAcquisition()
                        yield self.andor.WaitForAcquisitionTimeOut(int(timeouts[i]))
                        if self.andor.error['WaitForAcquisitionTimeOut'] != 20002:
                            print("Error acquiring frame {}: {}".format(i, self.andor.error['WaitForAcquisitionTimeOut']))
                            new_image = np.zeros(npixels)
                        else:
                            first, last = yield self.andor.GetNumberNewImages()
                            new_image, validfirst, validlast = yield self.andor.GetImages(first, last, npixels)
                        self.frames.append(new_image)
                else:
                    yield self.andor.StartAcquisition()
                    yield self.andor.WaitForAcquisitionTimeOut(int(timeouts[0]))
                    if self.andor.error['WaitForAcquisitionTimeOut'] != 20002:
                        print("Error acquiring: {}".format(self.andor.error['WaitForAcquisitionTimeOut']))
                        new_image = np.zeros(npixels)
                    else:
                        first, last = yield self.andor.GetNumberNewImages()
                        new_image, validfirst, validlast = yield self.andor.GetImages(first, last, npixels)
                    self.frames.append(new_image)

                yield self.andor.SetShutter(1, 2, 0, 0) # Close the shutter

                self.save_data(self.frames)

                # TODO: Why can't I read out all the images at the end?
                # first, last = yield self.andor.GetNumberNewImages()
                # print("first: {}, last: {}".format(first, last))
                # npixels = int((last - first) * kinFrames * dx * dy / (bin * bin))
                # data = yield self.andor.GetAcquiredData(npixels)
                # data, validfirst, validlast = yield self.andor.GetImages(first, last, npixels)

            except Exception as e:
                print_exc(e)