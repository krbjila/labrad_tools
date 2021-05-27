# -*- coding: utf-8 -*-

"""
@author: ziegler
"""

import numpy as np
import time

from .sdk import sdk
from .recorder import recorder


class exception(Exception):
    def __str__(self):
        return ('pco.exception Exception:', self.args)





class Camera(object):

    # -------------------------------------------------------------------------
    def __init__(self, debuglevel='off', timestamp='off', name='', interface=None):

        self.__debuglevel = debuglevel
        self.__timestamp = timestamp

        self.flim_config = None

        self.sdk = sdk(debuglevel=self.__debuglevel,
                       timestamp=self.__timestamp,
                       name=name)

        # self.sdk.open_camera()

        def __scanner(sdk, interfaces):

            for interface in interfaces:
                for camera_number in range(10):
                    ret = sdk.open_camera_ex(interface=interface, camera_number=camera_number)
                    
                    if ret['error'] == 0:
                        return 0
                    elif ret['error'] & 0x0000FFFF == 0x00002001:
                        continue
                    else:
                        break

            raise ValueError

        try:
            if interface is not None:
                if __scanner(self.sdk, [interface]) != 0:
                    raise ValueError
            else:
                if __scanner(self.sdk, ['CLHS', 'USB 3.0', 'Camera Link Silicon Software', 'USB 2.0', 'GigE']) != 0:
                    raise ValueError

        except ValueError:
            # print()
            # print('No camera found. Please check the connection and close '
            #       'other processes which use the camera.')
            # print()
            raise ValueError('No camera found. Please check the connection and close other processes which use the camera.')

        self.rec = recorder(self.sdk,
                            self.sdk.get_camera_handle(),
                            debuglevel=self.__debuglevel,
                            timestamp=self.__timestamp,
                            name=name)

        name = self.sdk.get_camera_name()
        self.metadata_enabled = any(supported in name for supported in ['pco.edge', 'pco.dimax', 'pco.dicam'])
        self.default_configuration()


    # -------------------------------------------------------------------------
    def default_configuration(self):
        """
        Sets default configuration for the camera.

        :rtype: None

        >>> default_configuration()

        """

        if self.sdk.get_recording_state()['recording state'] == 'on':
            self.sdk.set_recording_state('off')

        self.sdk.reset_settings_to_default()

        self.sdk.set_bit_alignment('LSB')

        if self.sdk.get_camera_description()['dwGeneralCapsDESC1'] & 0x00004000 == 0x00004000:
            self.sdk.set_metadata_mode('on')

        self.__serial = self.sdk.get_camera_type()['serial number']
        self.__camera_name = self.sdk.get_camera_name()['camera name']

        self.sdk.arm_camera()

    # -------------------------------------------------------------------------
    def __str__(self):
        return '{}, serial: {}'.format(self.__camera_name,
                                       self.__serial)

    # -------------------------------------------------------------------------
    def __repr__(self):
        return 'camera'

    # -------------------------------------------------------------------------
    @property
    def configuration(self):

        conf = {}

        exp = self.sdk.get_delay_exposure_time()
        timebase = {'ms': 1e-3, 'us': 1e-6, 'ns': 1e-9}
        time = exp['exposure'] * timebase[exp['exposure timebase']]
        conf.update({'exposure time': time})

        roi = self.sdk.get_roi()
        x0, y0, x1, y1 = roi['x0'], roi['y0'], roi['x1'], roi['y1']
        conf.update({'roi': (x0, y0, x1, y1)})

        conf.update({'timestamp': self.sdk.get_timestamp_mode()['timestamp mode']})
        conf.update({'pixel rate': self.sdk.get_pixel_rate()['pixel rate']})
        conf.update({'trigger': self.sdk.get_trigger_mode()['trigger mode']})
        conf.update({'acquire': self.sdk.get_acquire_mode()['acquire mode']})

        if self.metadata_enabled:
            conf.update({'metadata': self.sdk.get_metadata_mode()['metadata mode']})
        else:
            conf.update({'metadata': 'off'})

        bin = self.sdk.get_binning()
        conf.update({'binning': (bin['binning x'], bin['binning y'])})

        return conf


    # -------------------------------------------------------------------------
    @configuration.setter
    def configuration(self, arg):
        """
        Configures the camera with the given values from a dictionary.

        :param arg: Arguments to configurate the camera.
        :type arg: dict

        :rtype: None

        >>> configuration = {'exposure time': 10e-3,
                             'roi': (1, 1, 512, 512),
                             'timestamp': 'ascii'}

        """

        if type(arg) is not dict:
            print('Argument is not a dictionary')
            raise TypeError

        if self.sdk.get_recording_state()['recording state'] == 'on':
            self.sdk.set_recording_state('off')

        if 'exposure time' in arg:
            self.set_exposure_time(arg['exposure time'])

        if 'roi' in arg:
            self.sdk.set_roi(*arg['roi'])

        if 'timestamp' in arg:
            self.sdk.set_timestamp_mode(arg['timestamp'])

        if 'pixel rate' in arg:
            self.sdk.set_pixel_rate(arg['pixel rate'])

        if 'trigger' in arg:
            self.sdk.set_trigger_mode(arg['trigger'])

        if 'acquire' in arg:
            self.sdk.set_acquire_mode(arg['acquire'])

        if 'metadata' in arg and self.metadata_enabled:
            self.sdk.set_metadata_mode(arg['metadata'])

        if 'binning' in arg:
            self.sdk.set_binning(*arg['binning'])

        self.sdk.arm_camera()

    # -------------------------------------------------------------------------
    def record(self, number_of_images=1, mode='sequence'):
        """
        Generates and configures a new Recorder instance.

        :param number_of_images: Number of images allocated in the driver. The
                                 RAM of the PC is limiting the maximum value.
        :type number_of_images: int
        :paran mode: Mode of the Recorder
            * 'sequence' - function is blocking while the number of images are
                           recorded. Recorder stops the recording when the
                           maximum number of images is reached.
            * 'sequence non blocking' - function is non blocking. Status must
                                        be checked before reading the image.
            * 'ring buffer' - function is non blocking. Status must be checked
                              before reading the image. Recorder did not stop
                              the recording when the maximum number of images
                              is reached. The first image is overwritten from
                              the next image.
            * 'fifo' - function is non blocking. Status must be checked before
                       reading the image.
        :type mode: string

        >>> record()

        >>> record(10)

        >>> record(number_of_images=10, mode='sequence')

        >>> record(10, 'ring buffer')

        >>> record(20, 'fifo')

        """

        if (self.sdk.get_camera_health_status()['status'] & 2) != 2:
            self.sdk.arm_camera()

        self.__roi = self.sdk.get_roi()

        try:

            if self.sdk.get_camera_description()['wDoubleImageDESC'] == 1:
                if self.sdk.get_double_image_mode()['double image'] == 'on':
                    self.__roi['y1'] = self.__roi['y1'] * 2
        except Exception:
            pass

        if self.rec.recorder_handle.value is not None:
            self.rec.stop_record()
            self.rec.delete()

        if mode == 'sequence':
            blocking = 'on'
        elif mode == 'sequence non blocking':
            mode = 'sequence'
            blocking = 'off'
        elif mode == 'ring buffer':
            if number_of_images < 4:
                print('Please use 4 or more image buffer')
                raise ValueError
            blocking = 'off'
        elif mode == 'fifo':
            if number_of_images < 4:
                print('Please use 4 or more image buffer')
                raise ValueError
            blocking = 'off'
        else:
            raise ValueError

        m = self.rec.create('memory')['maximum available images']
        if m >= number_of_images:
            self.__number_of_images = number_of_images
        else:
            print('maximum available images:', m)
            raise ValueError

        self.rec.init(self.__number_of_images, mode)

        self.rec.set_compression_parameter()

        self.rec.start_record()

        if blocking == 'on':
            while True:
                running = self.rec.get_status()['is running']
                if running is False:
                    break
                time.sleep(0.001)
        #else:
        #    self.wait_for_image()

    # -------------------------------------------------------------------------
    def stop(self):
        """
        Stops the current recording. Is used in "ring buffer" mode or "fifo"
        mode.

        >>> stop()

        """
        if self.rec.recorder_handle.value is not None:
            self.rec.stop_record()

    # -------------------------------------------------------------------------
    def close(self):
        """
        Closes the current active camera and releases the blocked ressources.
        This function must be called before the application is terminated.
        Otherwise the resources remain occupied.

        This function is called automatically, if the camera object is
        created by the 'with' statement. An explicit call of 'close()' is no
        longer necessary.

        >>> close()

        >>> with pco.camera() as cam:
        ...:   # do some stuff

        """

        if self.rec.recorder_handle.value is not None:
            try:
                self.rec.stop_record()
            except self.rec.exception as exc:
                pass

        if self.rec.recorder_handle.value is not None:
            try:
                self.rec.delete()
            except self.rec.exception as exc:
                pass

        if self.sdk.lens_control.value is not None:
            try:
                self.sdk.close_lens_control()
            except self.sdk.exception as exc:
                pass

        try:
            self.sdk.close_camera()
        except self.sdk.exception as exc:
            pass

    # -------------------------------------------------------------------------
    def __enter__(self):

        return self

    # -------------------------------------------------------------------------
    def __exit__(self, type, value, traceback):

        self.close()

    # -------------------------------------------------------------------------
    def image(self, image_number=0, roi=None):
        """
        Returns an image from the recorder.

        :param image_number: Number of recorder index to read. In "sequence"
                             mode or "sequence non blocking" mode the recorder
                             index matches the image number.
        :type image_number: int
        :param roi: Region of interrest. Only this region is returned.
        :type roi: tuple(int, int, int, int)

        :return: image
        :rtype: numpy array

        >>> image(image_number=0, roi=(1, 1, 512, 512))
        image, metadata

        >>> image(0xFFFFFFFF)
        image, metadata

        """

        if roi is None:
            image = self.rec.copy_image(image_number, 1, 1,
                                        (self.__roi['x1'] - self.__roi['x0'] + 1),
                                        (self.__roi['y1'] - self.__roi['y0'] + 1))

            np_image = np.asarray(image['image']).reshape((self.__roi['y1']-self.__roi['y0']+1),
                                                          (self.__roi['x1']-self.__roi['x0']+1))

        else:
            image = self.rec.copy_image(image_number, roi[0], roi[1], roi[2], roi[3])
            np_image = np.asarray(image['image']).reshape((roi[3] - roi[1] + 1), (roi[2] - roi[0] + 1))

        meta = {}
        meta.update({'serial number': image['serial number']})
        meta.update({'camera image number': image['camera image number']})
        meta.update({'recorder image number': image['recorder image number']})
        meta.update({'size x': image['wIMAGE_SIZE_X']})
        meta.update({'size y': image['wIMAGE_SIZE_Y']})
        meta.update({'binning x': image['bBINNING_X']})
        meta.update({'binning y': image['bBINNING_Y']})
        meta.update({'conversion factor': image['conversion factor']})
        meta.update({'pixel clock': image['pixel clock']})
        meta.update({'sensor temperature': image['sensor temperature']})

        time.sleep(0.001)
        return np_image, meta

    # -------------------------------------------------------------------------
    def images(self, roi=None, blocksize=None,):
        """
        Returns all recorded images from the recorder.

        :param roi: Region of interrest. Only this region is returned.
        :type roi: tuple(int, int, int, int)

        :param blocksize: The blocksize defines the maximum number of images
                          which are returned. This parameter is only useful in
                          'fifo' mode and special conditions.
        :type blocksize: int

        :return: images
        :rtype: list(numpy arrays)

        >>> images()
        image_list, metadata_list

        >>> images(blocksize=8)
        image_list[:8], metadata_list[:8]

        """

        image_list = []
        meta_list = []

        if blocksize is None:

            for index in range(self.__number_of_images):

                if roi is None:
                    image = self.rec.copy_image(index, 1, 1,
                                                (self.__roi['x1'] - self.__roi['x0'] + 1),
                                                (self.__roi['y1'] - self.__roi['y0'] + 1))

                    np_image = np.asarray(image['image']).reshape((self.__roi['y1']-self.__roi['y0']+1),
                                                                  (self.__roi['x1']-self.__roi['x0']+1))

                else:
                    image = self.rec.copy_image(index, roi[0], roi[1], roi[2], roi[3])

                    np_image = np.asarray(image['image']).reshape((roi[3] - roi[1] + 1), (roi[2] - roi[0] + 1))

                meta = {}
                meta.update({'serial number': image['serial number']})
                meta.update({'camera image number': image['camera image number']})

                meta_list.append(meta)
                image_list.append(np_image)

        else:

            while True:
                level = self.rec.get_status()['dwProcImgCount']

                if level >= blocksize:
                    break

            for index in range(blocksize):

                if roi is None:
                    image = self.rec.copy_image(index, 1, 1,
                                                (self.__roi['x1'] - self.__roi['x0'] + 1),
                                                (self.__roi['y1'] - self.__roi['y0'] + 1))

                    np_image = np.asarray(image['image']).reshape((self.__roi['y1']-self.__roi['y0']+1),
                                                                  (self.__roi['x1']-self.__roi['x0']+1))

                else:
                    image = self.rec.copy_image(index, roi[0], roi[1], roi[2], roi[3])

                    np_image = np.asarray(image['image']).reshape((roi[3] - roi[1] + 1), (roi[2] - roi[0] + 1))

                meta = {}
                meta.update({'serial number': image['serial number']})
                meta.update({'camera image number': image['camera image number']})

                meta_list.append(meta)
                image_list.append(np_image)

        time.sleep(0.001)
        return image_list, meta_list


    # -------------------------------------------------------------------------
    def set_exposure_time(self, exposure_time):
        """
        Sets the exposure time of the camera. The underlying values for the
        sdk.set_delay_exposure_time(0, 'ms', time, timebase) function will be
        calculated automatically. The delay time is set to 0.

        >>> set_exposure_time(0.001)

        >>> set_exposure_time(1e-3)

        """

        if exposure_time <= 4e-3:
            time = int(exposure_time * 1e9)
            timebase = 'ns'

        elif exposure_time <= 4:
            time = int(exposure_time * 1e6)
            timebase = 'us'

        elif exposure_time > 4:
            time = int(exposure_time * 1e3)
            timebase = 'ms'

        else:
            raise

        self.sdk.set_delay_exposure_time(0, 'ms', time, timebase)

    # -------------------------------------------------------------------------
    def get_exposure_time(self):

        de = self.sdk.get_delay_exposure_time()

        exposure = de['exposure']
        timebase = de['exposure timebase']

        timebase_dict = {'ns': 1e-9, 'us': 1e-6, 'ms': 1e-3}

        exposure_time = timebase_dict[timebase] * exposure

        return exposure_time

    # -------------------------------------------------------------------------
    def image_average(self, roi=None):
        """
        Returns the averaged image. This image is calculated from all created
        image buffers.

        >>> average_image()
        image

        """

        start = 0
        stop = self.__number_of_images - 1

        if roi is None:
            image = self.rec.copy_average_image(start, stop,
                                                1, 1,
                                                (self.__roi['x1'] - self.__roi['x0'] + 1),
                                                (self.__roi['y1'] - self.__roi['y0'] + 1))

            np_image = np.asarray(image['average image']).reshape((self.__roi['y1']-self.__roi['y0']+1),
                                                                  (self.__roi['x1']-self.__roi['x0']+1))
        else:
            image = self.rec.copy_average_image(start, stop,
                                                 roi[0],  roi[1],
                                                 roi[2],  roi[3])

            np_image = np.asarray(image['average image']).reshape((roi[3] - roi[1] + 1), (roi[2] - roi[0] + 1))

        return np_image

     # -------------------------------------------------------------------------
    def average_image(self, roi=None):

        print()
        print('WARNING: This function will be removed / renamed. Use image_average() instead.')
        print()

        return self.image_average(roi)




    # -------------------------------------------------------------------------
    def wait_for_image(self):
        """
        This function waits for the first available image. In recorder mode
        'sequence non blocking', 'ring buffer' and 'fifo' the record() function
        returns immediately. The user is responsible to wait for images from
        the camera before image() / images() is called.

        >>> wait_for_image()

        """

        print()
        print('WARNING: This function will be removed / renamed. Use wait_for_first_image() instead.')
        print()

        self.wait_for_first_image()

    # -------------------------------------------------------------------------
    def wait_for_first_image(self):
        """
        This function waits for the first available image. In recorder mode
        'sequence non blocking', 'ring buffer' and 'fifo' the record() function
        returns immediately. The user is responsible to wait for images from
        the camera before image() / images() is called.

        >>> wait_for_first_image()

        """
        while True:

            if self.rec.get_status()['dwProcImgCount'] >= 1:
                break
            time.sleep(0.001)


    # -------------------------------------------------------------------------
    def image_compressed(self, image_number=0, roi=None):
        """
        Returns an image from the recorder.

        :param image_number: Number of recorder index to read. In "sequence"
                             mode or "sequence non blocking" mode the recorder
                             index matches the image number.
        :type image_number: int
        :param roi: Region of interrest. Only this region is returned.
        :type roi: tuple(int, int, int, int)

        :return: image
        :rtype: numpy array

        >>> image(image_number=0, roi=(1, 1, 512, 512))
        image, metadata

        >>> image(0xFFFFFFFF)
        image, metadata

        """

        if roi is None:
            image = self.rec.copy_image_compressed(image_number, 1, 1,
                                                   (self.__roi['x1'] - self.__roi['x0'] + 1),
                                                   (self.__roi['y1'] - self.__roi['y0'] + 1))

            np_image = np.asarray(image['image']).reshape((self.__roi['y1']-self.__roi['y0']+1),
                                                          (self.__roi['x1']-self.__roi['x0']+1))

        else:
            image = self.rec.copy_image_compressed(image_number, roi[0], roi[1], roi[2], roi[3])
            np_image = np.asarray(image['image']).reshape((roi[3] - roi[1] + 1), (roi[2] - roi[0] + 1))

        meta = {}
        meta.update({'serial number': image['serial number']})
        meta.update({'camera image number': image['camera image number']})
        meta.update({'recorder image number': image['recorder image number']})
        meta.update({'size x': image['wIMAGE_SIZE_X']})
        meta.update({'size y': image['wIMAGE_SIZE_Y']})
        meta.update({'binning x': image['bBINNING_X']})
        meta.update({'binning y': image['bBINNING_Y']})

        return np_image, meta





# -----------------------------------------------------------------------------
class camera(Camera):

    def __init__(self, debuglevel='off', timestamp='off', name='', interface=None):

        print("Class 'camera' has been renamed to 'Camera', please use the new name.")

        super().__init__(debuglevel=debuglevel, timestamp=timestamp, name=name, interface=interface)


