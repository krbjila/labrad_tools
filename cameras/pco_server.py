"""
Provides access to PCO cameras.

..
    ### BEGIN NODE INFO
    [info]
    name = pco
    version = 1
    description =
    instancename = %LABRADNODE%_pco

    [startup]
    cmdline = %PYTHON3% %FILE%
    timeout = 20

    [shutdown]
    message = 987654321
    timeout = 20
    ### END NODE INFO
"""
import os, sys
from labrad.server import LabradServer, setting

import json
import numpy as np
from warnings import warn
import time
import csv

sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..'))
from server_tools.hardware_interface_server import HardwareInterfaceServer
from cameras.lib import pco

PCO_TRIGGER_MODES = [
    'auto sequence',
    'software trigger',
    'external exposure start & software trigger',
    'external exposure control',
    'external synchronized',
    'fast external exposure control',
    'external CDS control',
    'slow external exposure control',
    'external synchronized HDSDI'
]

PCO_RECORD_MODES = [
    'sequence',
    'sequence non blocking',
    'ring buffer',
    'fifo',
]

PCO_RECORD_UNINIT = 0
PCO_RECORD_READY = 1
PCO_RECORD_RUNNING = 2

class PcoConfigError(Exception):
    """
    An error raised by an issue with the configuration of a PCO camera
    """
    def __init__(self, msg=''):
        super().__init__(msg)

class PcoRecordError(Exception):
    """
    An error raised by an issue with recording an image with a PCO camera
    """
    def __init__(self, msg=''):
        super().__init__(msg)

class PcoSaveError(Exception):
    """
    An error raised by an issue with saving an image with a PCO camera
    """
    def __init__(self, msg=''):
        super().__init__(msg)

class PcoServer(HardwareInterfaceServer):
    """Provides access to PCO cameras.
    
    Uses a modified version of the PCO Python library, found in :code:`cameras/lib/pco`. For more information, refer to the `PCO SDK <https://www.pco.de/fileadmin/fileadmin/user_upload/pco-manuals/pco.sdk_manual.pdf>`_ and `PCO Python library <https://pypi.org/project/pco/>`_ documentation.
    """
    name = '%LABRADNODE%_pco'
    cam_info = {}

    @staticmethod
    def get_camera_identifier(cam):
        """
        get_camera_identifier(cam)

        Args:
            cam (pco.Camera()): A PCO camera object

        Returns:
            str: Returns a string containing the camera type and serial number of the camera.
        """
        name = cam.sdk.get_camera_name()['camera name']
        serial = cam.sdk.get_camera_type()['serial number']
        return name + " ({})".format(serial)

    def refresh_available_interfaces(self):
        """
        refresh_available_interfaces(self)
        
        Fill :code:`self.interfaces` with available connections using PCO dll
        """
        for k, cam in self.interfaces.items():
            try:
                key = self.get_camera_identifier(cam)
                print('{} is still connected'.format(k))
            except:
                print('{} disconnected'.format(k))
                try:
                    cam.close()
                    del self.interfaces[key]
                    del self.cam_info[key]
                except Exception as e:
                    warn("Error closing {}: {}".format(k, e))

        while True:
            # pco.Camera() gets next available camera
            try:
                cam = pco.Camera()
                key = self.get_camera_identifier(cam)
                self.interfaces[key] = cam
                self.cam_info[key] = {
                    'caps': cam.sdk.get_camera_description(),'record_status': PCO_RECORD_UNINIT
                }
                print('connected to pco {}'.format(key))
            except ValueError: # If no camera found
                break
            except Exception as e:
                warn(e)
                break
    
    # Overwriting the version in HardwareInterfaceServer
    # to avoid calling refresh_available_interfaces on Exception
    def call_if_available(self, f, c, *args, **kwargs):
        try:
            interface = self.get_interface(c)
            ans = getattr(interface, f)(*args, **kwargs)
            return ans
        except:
            self.interface = self.get_interface(c)
            return getattr(interface, f)

    @setting(2)
    def close_camera(self, c):
        """close_camera(self, c)

        Close the PCO camera opened via :meth:`~server_tools.hardware_interface_server.HardwareInterfaceServer.select_interface`.

        Args:
            c: Labrad context
        """
        try:
            self.call_if_available('close', c)
            del self.interfaces[c['address']]
        except KeyError as e:
            warn('Camera not found: {}'.format(e))
    
    def _get_config(self, c):
        return self.call_if_available('configuration', c)

    @setting(3, returns='s')
    def get_config(self, c):
        """get_config(self, c)

        Get the camera configuration opened via :meth:`~server_tools.hardware_interface_server.HardwareInterfaceServer.select_interface`.

        Args:
            c: Labrad context

        Returns:
            str: JSON-dumped configuration dictionary
        """
        return json.dumps(self._get_config(c))

    def set_cam_config(self, c, key, val):
        if self._is_running(c):
            raise(PcoConfigError("Can't update configuration of {} while camera is recording.".format(c['address'])))
        else:
            cam = self.get_interface(c)
            config = cam.configuration
            config.update({key: val})
            cam.configuration = config

    @setting(4, returns='s')
    def get_capabilities(self, c):
        """
        get_capabilities(self, c)
        
        Gets a description of the camera, including available image sizes, readout rates, etc.

        Args:
            c: Labrad context

        Returns:
            str: JSON-dumped camera description dictionary
        """
        return json.dumps(self.cam_info[c['address']]['caps'])

    @setting(5, exposure='v', returns='v')
    def set_exposure(self, c, exposure):
        """
        set_exposure(self, c, exposure)

        Sets the camera exposure. If the specified exposure is outside the camera's exposure range, clips to the range and warns the user.

        Args:
            c: Labrad context
            exposure (numeric): Exposure in seconds.

        Returns:
            float: the camera's actual exposure setting in seconds.
        """
        caps = self.cam_info[c['address']]['caps']
        min_exp = caps['Min Expos DESC']*1e-9
        max_exp = caps['Max Expos DESC']*1e-3

        if exposure < min_exp:
            warn("Requested exposure {} is too short; setting to minimum: {}".format(exposure, min_exp))
            exposure = min_exp
        elif exposure > max_exp:
            warn("Requested exposure {} is too long; setting to maximum: {}".format(exposure, max_exp))
            exposure = max_exp
        self.set_cam_config(c, 'exposure time', exposure)
        return exposure

    ### Set ROI not supported on pixelfly!!! ###
    # @setting(6, xmin='i', xmax='i', ymin='i', ymax='i', returns='s')
    # def set_roi(self, c, xmin=None, ymin=None, xmax=None, ymax=None):
    #     caps = self.cam_info[c['address']]['caps']
    #     cam_xmin = cam_ymin = 1
    #     cam_xmax = caps['max. horizontal resolution standard']
    #     cam_ymax = caps['max. vertical resolution standard']

    #     if xmin is None:
    #         xmin = cam_xmin
    #     if ymin is None:
    #         ymin = cam_ymin
    #     if xmax is None:
    #         xmax = cam_xmax
    #     if ymax is None:
    #         ymax = cam_ymax

    #     xmin = min(max(cam_xmin, xmin), cam_xmax)
    #     xmax = max(min(cam_xmax, xmax), xmin)
    #     ymin = min(max(cam_ymin, ymin), cam_ymax)
    #     ymax = max(min(cam_ymax, ymax), ymin)

    #     self.set_cam_config(c, 'roi', [xmin, ymin, xmax, ymax])
    #     config = self.get_config(c)
    #     return json.dumps({'roi': config['roi']})

    @setting(7, returns='*i')
    def get_readout_rates(self, c):
        """get_readout_rates(self, c)

        Gets the possible readout rates for the selected camera, in pixels per second.

        Args:
            c: Labrad context

        Returns:
            [int]: the possible readout rates for the camera, in pixels per second
        """
        rates = self.cam_info[c['address']]['caps']['pixel rate']
        nonzero = [i for i in rates if i > 0]
        return nonzero

    @setting(8, readout='i', returns='i')
    def set_readout_rate(self, c, readout):
        """
        set_readout_rate(self, c, readout)

        Sets the readout rate for the selected camera, in pixels per second.

        Args:
            c: Labrad context
            readout (int): the readout rates for the camera, in pixels per second. Must be one of the values returned by :meth:`get_readout_rates`

        Returns:
            int: the camera's actual readout rate, in pixels per second
        """
        rates = self.get_readout_rates(c)
        if readout in rates:
            self.set_cam_config(c, 'pixel rate', readout)
        else:
            raise(PcoConfigError("Readout rate \"{}\" not supported on {}.".format(readout, c['address'])))
        return self._get_config(c)['pixel rate']

    @setting(9, returns='*s')
    def get_trigger_modes(self, c):
        """
        get_trigger_modes(self, c)

        Returns a list of the possible trigger modes for PCO cameras. Not all trigger modes may be compatible with the selected camera.

        Args:
            c: Labrad context

        Returns:
            [str]: a list of the possible trigger modes for PCO cameras.
        """
        return PCO_TRIGGER_MODES

    @setting(10, mode='s', returns='s')
    def set_trigger_mode(self, c, mode):
        """
        set_trigger_mode(self, c, mode)

        Sets the trigger mode for the selected camera.

        Args:
            c: Labrad context
            mode (str): The trigger mode for the camera. Must be one of the values returned by :meth:`get_trigger_modes`. Not all trigger modes work for all cameras.

        Returns:
            str: the camera's actual trigger mode
        """
        if mode in PCO_TRIGGER_MODES:
            try:
                self.set_cam_config(c, 'trigger', mode)
            except PcoConfigError as e:
                raise(e)
            except Exception as e:
                raise(PcoConfigError("Trigger mode \"{}\" not supported on {}.".format(mode, c['address'])))
        else:
            warn("Trigger mode \"{}\" not found; supported modes: {}.".format(mode, PCO_TRIGGER_MODES))    
        return self._get_config(c)['trigger']

    @setting(11, xbins='i', ybins='i', returns='*i')
    def set_binning(self, c, xbins, ybins=None):
        """
        set_binning(self, c, xbins, ybins=None)
        
        Sets the selected camera's binning mode.

        Args:
            c: Labrad context
            xbins (int): horizontal bin size
            ybins (int, optional): vertical bin size. Defaults to None, in which case it is set equal to xbins.

        Returns:
            [int]: the camera's actual horizontal and vertical bin sizes
        """
        if ybins is None:
            ybins = xbins
        try:
            self.set_cam_config(c, 'binning', [xbins, ybins])
        except PcoConfigError as e:
            raise(e)
        except Exception:
            raise(PcoConfigError("Binning [{}, {}] is not supported on {}".format(xbins, ybins, c['address'])))
        return self._get_config(c)['binning']
    
    @setting(12, returns='b')
    def get_interframing_enabled(self, c):
        """
        get_interframing_enabled(self, c)

        Checks whether interframing mode is enabled for the selected camera.

        Args:
            c: Labrad context

        Returns:
            bool: whether interframing mode is enabled for the selected camera
        """
        sdk = self.call_if_available('sdk', c)
        try:
            s = sdk.get_double_image_mode()['double image']
            return 'on' in s
        except Exception:
            warn('Interframing mode not available for {}'.format(c['address']))
            return False

    @setting(13, enable='b', returns='b')
    def set_interframing_enabled(self, c, enable):
        """
        set_interframing_enabled(self, c, enable)

        Sets whether interframing mode is enabled for the selected camera.

        Args:
            c: Labrad context
            enable (bool): [description]

        Returns:
            bool: whether interframing mode is actually enabled for the selected camera
        """
        sdk = self.call_if_available('sdk', c)
        s = 'on' if enable else 'off'

        if self._is_running(c):
            raise(PcoConfigError("Can't change interframing of {} while camera is recording.").format(c['address']))
        else:
            try:
                sdk.set_double_image_mode(s)
                return 'on' in sdk.get_double_image_mode()['double image']
            except:
                warn('Interframing mode not available for {}'.format(c['address']))
                return False

    def _is_running(self, c):
        status = self.cam_info[c['address']]['record_status']
        return status == PCO_RECORD_RUNNING

    @setting(14, returns='b')
    def is_running(self, c):
        """
        is_running(self, c)

        Checks whether the selected camera is currently recording.

        Args:
            c: Labrad context

        Returns:
            bool: whether the selected camera is currently recording
        """
        try:
            status = self._get_status(c)['is running']
            self.cam_info[c['address']]['record_status'] = PCO_RECORD_RUNNING if status else PCO_RECORD_READY
            return status
        except PcoRecordError:
            self.cam_info[c['address']]['record_status'] = PCO_RECORD_UNINIT
            warn("Recording not initialized.")
            return False

    @setting(15, n_images='i', mode='s')
    def start_record(self, c, n_images=1, mode='sequence non blocking'):
        """
        start_record(self, c, n_images=1, mode='sequence non blocking')

        Starts recording images on the selected camera.

        Args:
            c: Labrad context
            n_images (int, optional): The number of images to return. Defaults to 1.
            mode (str, optional): [description]. Defaults to 'sequence non blocking'.
        """
        # TODO: Allow recording infinite images? Do we need a stop recording function?
        self.call_if_available('record', c, n_images, mode)
        self.is_running(c)

    @setting(19, returns='i')
    def available_images(self, c):
        """
        available_images(self, c)

        Args:
            c: Labrad context

        Returns:
            int: Number of acquired images.
        """
        return self._get_status(c)['dwProcImgCount']

    def check_roi(self, c, xmin, ymin, xmax, ymax):
        """
        check_roi(self, c, xmin, ymin, xmax, ymax)

        Checks that the roi defined by (xmin, ymin, xmax, ymax) is allowed for the currently selected camera.

        Note that the camera pixels are 1-indexed in the PCO software.

        Args:
            c: Labrad context
            xmin (int): First selected horizontal pixel, 1-indexed
            ymin (int): Last selected horizontal pixel
            xmax (int): First selected vertical pixel, 1-indexed
            ymax (int): Last selected vertical pixel (inclusive)

        Returns:
            (int, int, int, int): Bounds-checked roi (xmin, ymin, xmax, ymax)
        """
        caps = self.cam_info[c['address']]['caps']
        cam_xmin = cam_ymin = 1
        cam_xmax = caps['max. horizontal resolution standard']
        cam_ymax = caps['max. vertical resolution standard']

        out_xmin = min(max(cam_xmin, xmin), cam_xmax)
        out_xmax = max(min(cam_xmax, xmax), cam_xmin)
        out_ymin = min(max(cam_ymin, ymin), cam_ymax)
        out_ymax = max(min(cam_ymax, ymax), cam_ymin)

        if out_xmin > out_xmax:
            temp = out_xmax
            out_xmax = out_xmin
            out_xmin = temp
        if out_ymin > out_ymax:
            temp = out_ymax
            out_ymax = out_ymin
            out_ymin = temp

        ins = (xmin, ymin, xmax, ymax)
        outs = (out_xmin, out_ymin, out_xmax, out_ymax)

        if any(i != o for (i, o) in zip(ins, outs)):
            warn("Requested roi {} is invalid; setting to {}".format(ins, outs))
        return outs

    def get_images(self, c, roi=None):
        """
        get_images(self, c)

        Provides the images stored in the camera buffer, if any. If :meth:`record` has not been run, throws a :class:`PcoRecordError`. If no images are available, returns empty metadata and image array.

        Args:
            c: Labrad context
            roi ((int), optional): A 4-tuple of integers (xmin, ymin, xmax, ymax) representing the bounds of the image to be saved. Defaults to None, in which case the whole image is saved.

        Returns:
            ([numpy array]): A list of numpy arrays of the images.
        """
        if self.available_images(c) > 0:
            res = self.call_if_available('images', c, roi=roi)
            (images, _) = res
            out = images
        else:
            warn("No images acquired.")
            out = []
        return out

    @setting(16, path='s', n_images='i', roi='*i', returns='s')
    def save_images(self, c, path, n_images, roi=None):
        """
        save_images(self, c, path, n_images, roi)

        Saves the latest `n_image` images if available. If :meth:`record` has not been run, throws a :class:`PcoRecordError`. If fewer than n_images have been acquired, throws a :class:`PcoSaveError`.

        The images are saved as a compressed `.npz<https://numpy.org/doc/stable/reference/generated/numpy.lib.format.html#module-numpy.lib.format>`_ format with fields "meta" containing a zero-dimensional array with a metadata dictionary (stored pickled) and a 3-dimensional integer ndarray of dimension (n_images, y dimension, x dimension) containing the images. Note that the two frames are stacked in a single image in y if interframing is enabled.
        
        Args:
            c: Labrad context
            path (str): Path to saved imaged. The extension is automatically changed to ".npz"
            n_images (int): Number of images to save.
            roi ((int), optional): A 4-tuple of integers (xmin, ymin, xmax, ymax) representing the bounds of the image to be saved. Defaults to None, in which case the whole image is saved.

        Returns:
            str: Path to saved image
        """
        if roi is not None:
            if len(roi) != 4:
                roi = None
            else:
                roi = self.check_roi(c, *roi)
        images = self.get_images(c, roi)
        
        if len(images) < n_images:
            raise(PcoSaveError("Fewer than {} images were recorded; only got {} images").format(n_images, len(images)))
        if len(images) > n_images:
            images = images[-n_images:]
        images = np.array(images)

        config = self._get_config(c)
        metadata = {
            'images': n_images,
            'interframing': 'on' if self.get_interframing_enabled(c) else 'off',
            'exposure': config['exposure time'],
            'acquire': config['acquire'],
            'binning': config['binning'],
            'roi': roi if roi is not None else config['roi'],
            'readout': config['pixel rate'],
            'trigger': config['trigger'],
            'timestamp': time.strftime("%H:%M:%S", time.localtime())
        }

        # Define a temporary path to avoid conflicts when writing file
		# Otherwise, fitting program autoloads the file before writing is complete
        path = os.path.splitext(path)[0]+".npz"
        path_temp = path + "_temp"
        with open(path_temp, 'wb') as f:
            np.savez_compressed(f, data=images, meta=metadata)
        # Once file is written, rename to the correct filename
        os.rename(path_temp, path)
        return path

    def _get_status(self, c):
        try:
            rec = self.call_if_available('rec', c)
            status = rec.get_status()
            return status
        except:
            raise(PcoRecordError("Recording not started!"))
        
    @setting(17, returns='s')
    def get_status(self, c):
        """
        get_status(self, c)

        Gets the recording status of the current camera. Returns an empty JSON if recording is not initialized.

        Args:
            c: Labrad context

        Returns:
            str: JSON-dumped recording status
        """
        try:
            out = self._get_status(c)
        except PcoRecordError as e:
            warn("Recording not initialized.")
            out = {}
        return json.dumps(out)

    @setting(18)
    def stop_record(self, c):
        """
        stop_record(self, c)

        Stop recording on the current camera.

        Args:
            c: Labrad context
        """
        self.call_if_available('stop', c)
        
        still_running = self.is_running(c) # sets self.cam_info[c['address']]['record_status']
        if still_running:
            raise(PcoRecordError("Problem stopping record."))
        

    def stopServer(self):
        """
        stopServer(self)

        Closes camera connections and shuts down the Labrad server.
        """
        for cam in self.interfaces.values():
            try:
                cam.stop()
            except Exception as e:
                warn(e)
        super().stopServer()

    # @setting(6, timeout='v', returns='v')
    # def timeout(self, c, timeout=None):
    #     """Sets the timeout associated with the interface

    #     Args:
    #         c: The LabRAD context
    #         timeout (numeric, optional): The timeout for the interface in seconds. Defaults to None.

    #     Returns:
    #         The timeout in seconds
    #     """
    #     interface = self.get_interface(c)
    #     if timeout is not None:
    #         interface.timeout = timeout
    #     return interface.timeout


if __name__ == '__main__':
    from labrad import util
    util.runServer(PcoServer())