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
import json

from pymongo import MongoClient
import gridfs

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
        self.conductor = self.cxn.conductor
        self.logging = self.cxn.imaging_logging

        try:
            with open('/home/bialkali/labrad_tools/conductor/devices/andor/mongodb.json', 'r') as f:
                mongo_config = json.load(f)
            self.database = yield MongoClient(mongo_config['address'], mongo_config['port'], username=mongo_config['user'], password=mongo_config['password']).data
            self.gfs = gridfs.GridFS(self.database)
            print("{} connected to MongoDB".format(self.__class__.__name__))
        except Exception as e:
            self.database = None
            print("{} could not connect to MongoDB".format(self.__class__.__name__))
            print_exc(e)

        cameras = yield self.andor.get_interface_list()
        if self.serial not in cameras:
            raise Exception('Camera {} not found'.format(self.serial))
        yield self.andor.select_interface(self.serial)

        yield self.andor.AbortAcquisition()
        yield self.andor.CancelWait()

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
    def save_data(self, frames, save_file=True, save_db=True):
        expected_frame_size = self.kinFrames * self.dy * self.dx / (self.bin * self.bin)
        if len(frames) < self.acqLength:
            print("Expected {} frames, got {}. Saving blank image".format(self.acqLength, len(frames)))
            frames = np.zeros(self.acqLength * expected_frame_size)
        data = np.array(frames)

        # uninterleave the fk frames
        if self.kinFrames > 1:
            data = data.reshape((-1, self.kinFrames, self.dy/self.bin, self.dx/self.bin))
            data = np.swapaxes(data, 0, 1)
        data = data.reshape((-1, self.dy/self.bin, self.dx/self.bin))

        if self.rotateImage:
            data = np.flip(np.swapaxes(np.array(data), 1, 2), axis=-1)

        now = datetime.now()

        metadata = {
            'camera': 'Andor iXon 888',
            'name': self.__class__.__name__,
            'serial': self.serial,
            'images': self.acqLength * self.kinFrames,
            'width': self.dx,
            'height': self.dy,
            'x_offset': self.xOffset,
            'y_offset': self.yOffset,
            'kinetics_frames': self.kinFrames,
            'exposure': self.expTime,
            'binning': (self.bin, self.bin),
            'timestamp': now.strftime("%Y-%m-%d %H:%M:%S"),
            'em_enable': 'on' if self.emEnable else 'off',
            'em_gain': self.emGain,
            'preamp_gain': self.preAmpGain,
            'vs_speed': self.vss,
            'shot': self.shot,
            'temperature': self.current_temp,
        }

        if save_db:
            if self.database:
                id = now.strftime("%Y_%m_%d_{}").format(self.shot)
                # See here for format: https://stackoverflow.com/questions/49493493/python-store-cv-image-in-mongodb-gridfs
                imageID = self.gfs.put(data.tobytes(), _id=id+"_{}".format(self.__class__.__name__), shape=data.shape, dtype=str(data.dtype))
                metadata['imageID'] = imageID
                update = [{
                    "$set": {
                        "images": {
                            metadata["image_id"]: metadata
                        }
                    },
                }]
                try:
                    update_value = yield self.database.shots.update_one({"_id": id}, update, upsert=True)
                    print("Saved image to MongoDB with id {}: {}".format(id, update_value))
                except Exception as e:
                    print("Could not save to MongoDB:")
                    print_exc(e)
            else:
                print("Could not save to MongoDB: not connected")

        if save_file:
            savedir = "/dataserver/data/"+datetime.now().strftime("%Y/%m/%Y%m%d/")+self.saveFolder+"/"
            file_number = 0
            if not os.path.exists(savedir):
                os.makedirs(savedir)
            else:
                filelist = os.listdir(savedir)
                file_number = 0
                for f in filelist:
                    match = re.match(self.filebase+"_([0-9]+).npz", f)
                    if match and int(match.group(1)) >= file_number:
                        file_number = int(match.group(1)) + 1

            path = savedir+self.filebase+"_"+str(file_number)

            print("Saving image to {}...".format(path+".npz"))

            metadata['parameters'] = json.loads(self.parameters)

            # spawn a new process to save the data to prevent hanging
            p = mp.Process(target=self.save_data_process, args=(path, data, metadata))
            p.start()

    def save_data_process(self, path, data, metadata):
        # Define a temporary path to avoid conflicts when writing file
        # Otherwise, fitting program autoloads the file before writing is complete
        path_temp = path+"_temp.npz"
        with open(path_temp, 'wb') as f:
            np.savez_compressed(f, data=data, meta=metadata)
        os.rename(path_temp, path+".npz")
        print("Saved image to {}".format(path+".npz"))

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
                self.saveFolder = self.value['saveFolder']
                self.filebase = self.value['filebase']
                self.rotateImage = self.value['rotateImage']
                self.timeouts = self.value['timeouts']

                self.parameters = yield self.conductor.get_parameter_values()
                self.shot = yield self.logging.get_shot()

                if 'temperature' in self.value and self.value['temperature'] != self.temperature:
                    self.temperature = self.value['temperature']
                    yield self.andor.SetTemperature(self.temperature)

                if 'save_file' in self.value:
                    save_file = self.value['save_file']
                else:
                    save_file = True

                if 'save_db' in self.value:
                    save_db = self.value['save_db']
                else:
                    save_db = True

                self.current_temp = yield self.andor.GetTemperature()
                print("Current temperature: {}".format(self.current_temp))
                if float(self.current_temp) > 0:
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

                self.andor.SetShutter(1, 1, 0, 0) # Open the shutter

                self.frames = []
                npixels = int(self.kinFrames * self.dx * self.dy / (self.bin * self.bin))

                if self.kinFrames > 1 and self.acqLength > 1:
                    for i in range(self.acqLength):
                        yield self.andor.StartAcquisition()
                        yield self.andor.WaitForAcquisitionTimeOut(int(self.timeouts[i]))
                        if self.andor.error['WaitForAcquisitionTimeOut'] != 20002:
                            print("Error acquiring frame {}: {}".format(i, self.andor.error['WaitForAcquisitionTimeOut']))
                            break
                        else:
                            first, last = yield self.andor.GetNumberNewImages()
                            new_image, validfirst, validlast = yield self.andor.GetImages(first, last, npixels)
                            self.frames.append(new_image)
                else:
                    yield self.andor.StartAcquisition()
                    yield self.andor.WaitForAcquisitionTimeOut(int(self.timeouts[0]))
                    if self.andor.error['WaitForAcquisitionTimeOut'] != 20002:
                        print("Error acquiring: {}".format(self.andor.error['WaitForAcquisitionTimeOut']))
                    else:
                        first, last = yield self.andor.GetNumberNewImages()
                        new_image, validfirst, validlast = yield self.andor.GetImages(first, last, npixels)
                        self.frames.append(new_image)

                yield self.andor.SetShutter(1, 2, 0, 0) # Close the shutter

                yield self.save_data(self.frames, save_file, save_db)

                # TODO: Why can't I read out all the images at the end?
                # first, last = yield self.andor.GetNumberNewImages()
                # print("first: {}, last: {}".format(first, last))
                # npixels = int((last - first) * kinFrames * dx * dy / (bin * bin))
                # data = yield self.andor.GetAcquiredData(npixels)
                # data, validfirst, validlast = yield self.andor.GetImages(first, last, npixels)

            except Exception as e:
                print_exc(e)