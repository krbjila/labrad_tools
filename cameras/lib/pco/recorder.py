# -*- coding: utf-8 -*-

"""
@author: ziegler
"""

import ctypes as C
import sys
import os
import time
from datetime import datetime
import platform


class recorder:

    class exception(Exception):
        def __str__(self):
            return ("Exception: {0} {1:08x}".format(self.args[0],
                                                    self.args[1] & (2**32-1)))

    def __init__(self, sdk, camera_handle, debuglevel='off', timestamp='off', name=''):

        if platform.architecture()[0] != '64bit':
            print('Python Interpreter not x64')
            raise OSError

        self.__dll_name = 'PCO_Recorder.dll'
        dll_path = os.path.dirname(__file__).replace('\\', '/')

        # set working directory
        # workaround, due to implicied load of PCO_File.dll
        current_working_directory = os.getcwd()
        os.chdir(dll_path)

        try:
            self.PCO_Recorder = C.windll.LoadLibrary(dll_path + '/' + self.__dll_name)
        except OSError:
            print('Error: ' + '"' + self.__dll_name + '" not found in directory "' + dll_path + '".')
            os.chdir(current_working_directory)
            raise

        os.chdir(current_working_directory)

        self.recorder_handle = C.c_void_p(0)
        self.camera_handle = camera_handle
        self.sdk = sdk

        self.debuglevel = debuglevel
        self.timestamp = timestamp
        self.name = name

    # -------------------------------------------------------------------------
    def log(self, name, error, data=None, start_time=0.0):

        if self.timestamp == 'on' and self.debuglevel != 'off':
            curr_time = datetime.now()
            formatted_time = curr_time.strftime('%Y-%m-%d %H:%M:%S.%f')
            ts = '[{0} /{1:6.3f} s] '.format(formatted_time, time.time() - start_time)
        else:
            ts = ''

        if self.debuglevel == 'error' and error != 0:
            print(ts + '[' + self.name + ']' + '[rec] ' + name + ':', self.sdk.get_error_text(error))
        elif self.debuglevel == 'verbose':
            print(ts + '[' + self.name + ']' + '[rec] ' + name + ':', self.sdk.get_error_text(error))
        elif self.debuglevel == 'extra verbose':
            print(ts + '[' + self.name + ']' + '[rec] ' + name + ':', self.sdk.get_error_text(error))
            if data is not None:
                for key, value in data.items():
                    print('   -', key + ':', value)

    # -------------------------------------------------------------------------
    # 2.1 PCO_RecorderGetVersion
    # -------------------------------------------------------------------------
    def get_version(self):
        """
        """

        self.PCO_Recorder.PCO_RecorderGetVersion.argtypes = [C.POINTER(C.c_int),
                                                             C.POINTER(C.c_int),
                                                             C.POINTER(C.c_int),
                                                             C.POINTER(C.c_int)]
        iMajor = C.c_int()
        iMinor = C.c_int()
        iPatch = C.c_int()
        iBuild = C.c_int()

        start_time = time.time()
        error = self.PCO_Recorder.PCO_RecorderGetVersion(iMajor,
                                                         iMinor,
                                                         iPatch,
                                                         iBuild)

        ret = {}
        if error == 0:
            ret.update({'name': self.__dll_name,
                        'major': iMajor.value,
                        'minor': iMinor.value,
                        'patch': iPatch.value,
                        'build': iBuild.value})

        self.log(sys._getframe().f_code.co_name, error, ret, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)
        return ret

    # -------------------------------------------------------------------------
    # 2.2 PCO_RecorderResetLib
    # -------------------------------------------------------------------------
    def reset_lib(self):
        """
        """

        self.PCO_Recorder.PCO_RecorderResetLib.argtypes = [C.c_bool]

        bSilent = C.c_bool(True)

        start_time = time.time()
        error = self.PCO_Recorder.PCO_RecorderResetLib(bSilent)

        self.recorder_handle = C.c_void_p(0)

        self.log(sys._getframe().f_code.co_name, error, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)

    # -------------------------------------------------------------------------
    # 2.3 PCO_RecorderCreate
    # -------------------------------------------------------------------------
    def create(self, mode):
        """
        """

        self.recorder_handle = C.c_void_p(0)
        self.PCO_Recorder.PCO_RecorderCreate.argtypes = [C.POINTER(C.c_void_p),
                                                         C.POINTER(C.c_void_p),
                                                         C.POINTER(C.c_uint32),
                                                         C.c_uint16,
                                                         C.c_uint16,
                                                         C.c_char,
                                                         C.POINTER(C.c_uint32)]

        recorder_mode = {'file': 1, 'memory': 2, 'camram': 3}

        dwImgDistributionArr = C.c_uint32(1)
        wArrLength = C.c_uint16(1)
        wRecMode = C.c_uint16()
        cDriveLetter = C.c_char('C'.encode('ASCII'))
        dwMaxImgCountArr = C.c_uint32()

        wRecMode = recorder_mode[mode]

        start_time = time.time()
        error = self.PCO_Recorder.PCO_RecorderCreate(self.recorder_handle,
                                                     self.camera_handle,
                                                     dwImgDistributionArr,
                                                     wArrLength,
                                                     wRecMode,
                                                     cDriveLetter,
                                                     dwMaxImgCountArr)

        ret = {}
        if error == 0:
            ret.update({'maximum available images': dwMaxImgCountArr.value})

        self.log(sys._getframe().f_code.co_name, error, ret, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)
        return ret

    # -------------------------------------------------------------------------
    # 2.4 PCO_RecorderDelete
    # -------------------------------------------------------------------------
    def delete(self):
        """
        """

        self.PCO_Recorder.PCO_RecorderDelete.argtypes = [C.c_void_p]

        start_time = time.time()
        error = self.PCO_Recorder.PCO_RecorderDelete(self.recorder_handle)

        self.recorder_handle = C.c_void_p(0)

        self.log(sys._getframe().f_code.co_name, error, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)

    # -------------------------------------------------------------------------
    # 2.5 PCO_RecorderInit
    # -------------------------------------------------------------------------
    def init(self, number_of_images, recorder_type):
        """
        """

        self.PCO_Recorder.PCO_RecorderInit.argtypes = [C.c_void_p,
                                                       C.POINTER(C.c_uint32),
                                                       C.c_uint16,
                                                       C.c_uint16,
                                                       C.c_uint16,
                                                       C.c_char_p,
                                                       C.POINTER(C.c_uint16)]

        dwImgCountArr = (C.c_uint32(number_of_images))
        wArrLength = C.c_uint16(1)
        wType = C.c_uint16()
        wNoOverwrite = C.c_uint16(0)
        szFilePath = 'C:/'
        pszFilePath = C.cast(szFilePath,  C.c_char_p)
        wRamSegmentArr = C.c_uint16()

        recorder_mode_file = {'tif': 1, 'multitif': 2, 'pcoraw': 3, 'b16': 4}
        recorder_mode_memory = {'sequence': 1, 'ring buffer': 2, 'fifo': 3}
        recorder_mode_camram = {'sequential': 1, 'single image': 2}

        wType = recorder_mode_memory[recorder_type]

        start_time = time.time()
        error = self.PCO_Recorder.PCO_RecorderInit(self.recorder_handle,
                                                   dwImgCountArr,
                                                   wArrLength,
                                                   wType,
                                                   wNoOverwrite,
                                                   pszFilePath,
                                                   wRamSegmentArr)

        self.log(sys._getframe().f_code.co_name, error, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)

    # -------------------------------------------------------------------------
    # 2.6 PCO_RecorderCleanup
    # -------------------------------------------------------------------------
    def cleanup(self):
        """
        """

        self.PCO_Recorder.PCO_RecorderCleanup.argtypes = [C.c_void_p,
                                                          C.c_void_p]

        start_time = time.time()
        error = self.PCO_Recorder.PCO_RecorderInit(self.recorder_handle,
                                                   self.camera_handle)

        self.log(sys._getframe().f_code.co_name, error, ret, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)

    # -------------------------------------------------------------------------
    # 2.7 PCO_RecorderGetSettings
    # -------------------------------------------------------------------------
    def get_settings(self):
        """
        """

        self.PCO_Recorder.PCO_RecorderGetSettings.argtypes = [C.c_void_p,
                                                              C.c_void_p,
                                                              C.POINTER(C.c_uint32),
                                                              C.POINTER(C.c_uint32),
                                                              C.POINTER(C.c_uint32),
                                                              C.POINTER(C.c_uint16),
                                                              C.POINTER(C.c_uint16),
                                                              C.POINTER(C.c_uint16)]

        dwRecmode = C.c_uint32()
        dwMaxImgCount = C.c_uint32()
        dwReqImgCount = C.c_uint32()
        wWidth = C.c_uint16()
        wHeight = C.c_uint16()
        wMetadataLines = C.c_uint16()

        start_time = time.time()
        error = self.PCO_Recorder.PCO_RecorderGetSettings(self.recorder_handle,
                                                          self.camera_handle,
                                                          dwRecmode,
                                                          dwMaxImgCount,
                                                          dwReqImgCount,
                                                          wWidth,
                                                          wHeight,
                                                          wMetadataLines)

        ret = {}
        if error == 0:
            ret.update({'recorder mode': dwRecmode.value})
            ret.update({'maximum number of images': dwMaxImgCount.value})
            ret.update({'required number of images': dwReqImgCount.value})
            ret.update({'width': wWidth.value})
            ret.update({'height': wHeight.value})
            ret.update({'metadata lines': wMetadataLines.value})


        self.log(sys._getframe().f_code.co_name, error, ret, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)
        return ret

    # -------------------------------------------------------------------------
    # 2.8 PCO_RecorderStartRecord
    # -------------------------------------------------------------------------
    def start_record(self):
        """
        """
        self.PCO_Recorder.PCO_RecorderStartRecord.argtypes = [C.c_void_p,
                                                              C.c_void_p]

        start_time = time.time()
        error = self.PCO_Recorder.PCO_RecorderStartRecord(self.recorder_handle,
                                                          self.camera_handle)

        self.log(sys._getframe().f_code.co_name, error, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)

    # -------------------------------------------------------------------------
    # 2.9 PCO_RecorderStopRecord
    # -------------------------------------------------------------------------
    def stop_record(self):
        """
        """

        self.PCO_Recorder.PCO_RecorderStopRecord.argtypes = [C.c_void_p,
                                                             C.c_void_p]

        start_time = time.time()
        error = self.PCO_Recorder.PCO_RecorderStopRecord(self.recorder_handle,
                                                         self.camera_handle)

        self.log(sys._getframe().f_code.co_name, error, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)

    # -------------------------------------------------------------------------
    # 2.10 PCO_RecorderSetAutoExposure
    # -------------------------------------------------------------------------
    def set_auto_exposure(self,
                          mode,
                          smoothness=2,
                          min_exposure_time=1e-3,
                          max_exposure_time=100e-3):
        """
        Set auto exposure

        :param active: bool
        :param smoothness: int
        :param min_exposure_time: float
        :param max_exposure_time: float
        """

        self.PCO_Recorder.PCO_RecorderSetAutoExposure.argtypes = [C.c_void_p,
                                                                  C.c_void_p,
                                                                  C.c_bool,
                                                                  C.c_uint16,
                                                                  C.c_uint32,
                                                                  C.c_uint32,
                                                                  C.c_uint16]

        if mode == 'on':
             active=True
        else:
            active=False

        # Only check min for timebase, since max is always greater
        if min_exposure_time <= 4e-3:
            min_time = int(min_exposure_time * 1e9)
            max_time = int(max_exposure_time * 1e9)
            timebase = 0  # ns

        elif min_exposure_time <= 4:
            min_time = int(min_exposure_time * 1e6)
            max_time = int(max_exposure_time * 1e6)
            timebase = 1  # us

        elif min_exposure_time > 4:
            min_time = int(min_exposure_time * 1e3)
            max_time = int(max_exposure_time * 1e3)
            timebase = 2  # ms

        else:
            raise

        start_time = time.time()
        error = self.PCO_Recorder.PCO_RecorderSetAutoExposure(self.recorder_handle,
                                                              self.camera_handle,
                                                              active,
                                                              smoothness,
                                                              min_time,
                                                              max_time,
                                                              timebase)

        self.log(sys._getframe().f_code.co_name, error, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)

    # -------------------------------------------------------------------------
    # 2.11 PCO_RecorderSetAutoExpRegions
    # -------------------------------------------------------------------------
    def set_auto_exposure_regions(self,
                                  region_type='balanced',
                                  region_array=[(0, 0)]):
        """
        Set auto exposure regions

        :param region_type: string
        :param region_type: List of Tupels
                            (only needed for region_type = custom)
        """

        self.PCO_Recorder.PCO_RecorderSetAutoExpRegions.argtypes = [C.c_void_p,
                                                                    C.c_void_p,
                                                                    C.c_uint16,
                                                                    C.POINTER(C.c_uint16),
                                                                    C.POINTER(C.c_uint16),
                                                                    C.c_uint16]

        types = {'balanced': 0,
                 'center based': 1,
                 'corner based': 2,
                 'full': 3,
                 'custom': 4}

        array_length = len(region_array)
        x0_array, y0_array = zip(*region_array)

        wRegionType = types[region_type]
        wRoiX0Arr = (C.c_uint16 * array_length)(*x0_array)
        wRoiY0Arr = (C.c_uint16 * array_length)(*y0_array)

        start_time = time.time()
        error = self.PCO_Recorder.PCO_RecorderSetAutoExpRegions(self.recorder_handle,
                                                                self.camera_handle,
                                                                wRegionType,
                                                                wRoiX0Arr,
                                                                wRoiY0Arr,
                                                                array_length)

        self.log(sys._getframe().f_code.co_name, error, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)

    # -------------------------------------------------------------------------
    # 2.xx PCO_RecorderSetCompressionParams
    # -------------------------------------------------------------------------
    def set_compression_parameter(self,
                                  gain=(1/0.46),
                                  dark_noise=1.5,
                                  dsnu=0.3,
                                  prnu=0.34):
        """
        """

        class PCO_RECORDER_COMPRESSION_PARAMETER(C.Structure):
            _pack_ = 1
            _fields_ = [
                ("dGainK", C.c_double),
                ("dDarkNoise_e", C.c_double),
                ("dDSNU_e", C.c_double),
                ("dPRNU_pct", C.c_double),
                ("dLightSourceNoise_pct", C.c_double)]

        self.PCO_Recorder.PCO_RecorderSetCompressionParams.argtypes = [C.c_void_p,
                                                                       C.c_void_p,
                                                                       C.POINTER(PCO_RECORDER_COMPRESSION_PARAMETER)]

        parameter = PCO_RECORDER_COMPRESSION_PARAMETER()

        parameter.dGainK = C.c_double(gain)
        parameter.dDarkNoise_e = C.c_double(dark_noise)
        parameter.dDSNU_e = C.c_double(dsnu)
        parameter.dPRNU_pct = C.c_double(prnu)
        parameter.dLightSourceNoise_pct = C.c_double(0)


        start_time = time.time()
        error = self.PCO_Recorder.PCO_RecorderSetCompressionParams(self.recorder_handle,
                                                                   self.camera_handle,
                                                                   parameter)

        self.log(sys._getframe().f_code.co_name, error, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)

    # -------------------------------------------------------------------------
    # 2.12 PCO_RecorderGetStatus
    # -------------------------------------------------------------------------
    def get_status(self):
        """
        """
        self.PCO_Recorder.PCO_RecorderGetStatus.argtypes = [C.c_void_p,
                                                            C.c_void_p,
                                                            C.POINTER(C.c_bool),
                                                            C.POINTER(C.c_bool),
                                                            C.POINTER(C.c_uint32),
                                                            C.POINTER(C.c_uint32),
                                                            C.POINTER(C.c_uint32),
                                                            C.POINTER(C.c_bool),
                                                            C.POINTER(C.c_bool),
                                                            C.POINTER(C.c_uint32),
                                                            C.POINTER(C.c_uint32)]

        bIsRunning = C.c_bool()
        bAutoExpState = C.c_bool()
        dwLastError = C.c_uint32()
        dwProcImgCount = C.c_uint32()
        dwReqImgCount = C.c_uint32()
        bBuffersFull = C.c_bool()
        bFIFOOverflow = C.c_bool()
        dwStartTime = C.c_uint32()
        dwStopTime = C.c_uint32()

        # Logging disabled
        # start_time = time.time()
        error = self.PCO_Recorder.PCO_RecorderGetStatus(self.recorder_handle,
                                                        self.camera_handle,
                                                        bIsRunning,
                                                        bAutoExpState,
                                                        dwLastError,
                                                        dwProcImgCount,
                                                        dwReqImgCount,
                                                        bBuffersFull,
                                                        bFIFOOverflow,
                                                        dwStartTime,
                                                        dwStopTime)

        ret = {}
        if error == 0:
            ret.update({'is running': bIsRunning.value})
            ret.update({'dwLastError': dwLastError.value})
            ret.update({'dwProcImgCount': dwProcImgCount.value})
            ret.update({'dwReqImgCount': dwReqImgCount.value})
            ret.update({'bBuffersFull': bBuffersFull.value})
            ret.update({'bFIFOOverflow': bFIFOOverflow.value})
            ret.update({'dwStartTime': dwStartTime.value})
            ret.update({'dwStopTime': dwStopTime.value})

        # Logging disabled
        # self.log(sys._getframe().f_code.co_name, error, ret, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)
        return ret

    # -------------------------------------------------------------------------
    # 2.13 PCO_RecorderGetImageAddress
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # 2.14 PCO_RecorderCopyImage
    # -------------------------------------------------------------------------
    def copy_image(self, index, x0, y0, x1, y1):
        """
        """

        class PCO_METADATA_STRUCT(C.Structure):
            _pack_ = 1
            _fields_ = [
                ("wSize", C.c_uint16),
                ("wVersion", C.c_uint16),
                ("bIMAGE_COUNTER_BCD", C.c_uint8 * 4),
                ("bIMAGE_TIME_US_BCD", C.c_uint8 * 3),
                ("bIMAGE_TIME_SEC_BCD", C.c_uint8),
                ("bIMAGE_TIME_MIN_BCD", C.c_uint8),
                ("bIMAGE_TIME_HOUR_BCD", C.c_uint8),
                ("bIMAGE_TIME_DAY_BCD", C.c_uint8),
                ("bIMAGE_TIME_MON_BCD", C.c_uint8),
                ("bIMAGE_TIME_YEAR_BCD", C.c_uint8),
                ("bIMAGE_TIME_STATUS", C.c_uint8),
                ("wEXPOSURE_TIME_BASE", C.c_uint16),
                ("dwEXPOSURE_TIME", C.c_uint32),
                ("dwFRAMERATE_MILLIHZ", C.c_uint32),
                ("sSENSOR_TEMPERATURE", C.c_short),
                ("wIMAGE_SIZE_X", C.c_uint16),
                ("wIMAGE_SIZE_Y", C.c_uint16),
                ("bBINNING_X", C.c_uint8),
                ("bBINNING_Y", C.c_uint8),
                ("dwSENSOR_READOUT_FREQUENCY", C.c_uint32),
                ("wSENSOR_CONV_FACTOR", C.c_uint16),
                ("dwCAMERA_SERIAL_NO", C.c_uint32),
                ("wCAMERA_TYPE", C.c_uint16),
                ("bBIT_RESOLUTION", C.c_uint8),
                ("bSYNC_STATUS", C.c_uint8),
                ("wDARK_OFFSET", C.c_uint16),
                ("bTRIGGER_MODE", C.c_uint8),
                ("bDOUBLE_IMAGE_MODE", C.c_uint8),
                ("bCAMERA_SYNC_MODE", C.c_uint8),
                ("bIMAGE_TYPE", C.c_uint8),
                ("wCOLOR_PATTERN", C.c_uint16)]

        class PCO_TIMESTAMP_STRUCT(C.Structure):
            _pack_ = 1
            _fields_ = [
                ("wSize", C.c_uint16),
                ("dwImgCounter", C.c_uint32),
                ("wYear", C.c_uint16),
                ("wMonth", C.c_uint16),
                ("wDay", C.c_uint16),
                ("wHour", C.c_uint16),
                ("wMinute", C.c_uint16),
                ("wSecond", C.c_uint16),
                ("dwMicroSeconds", C.c_uint32)]

        self.PCO_Recorder.PCO_RecorderCopyImage.argtypes = [C.c_void_p,
                                                            C.c_void_p,
                                                            C.c_uint32,
                                                            C.c_uint16,
                                                            C.c_uint16,
                                                            C.c_uint16,
                                                            C.c_uint16,
                                                            C.POINTER(C.c_uint16),
                                                            C.POINTER(C.c_uint32),
                                                            C.POINTER(PCO_METADATA_STRUCT),
                                                            C.POINTER(PCO_TIMESTAMP_STRUCT)]

        image = (C.c_uint16 * (((x1-x0)+1)*((y1-y0)+1)))()
        p_wImgBuf = C.cast(image, C.POINTER(C.c_uint16))
        dwImgNumber = C.c_uint32()
        metadata = PCO_METADATA_STRUCT()
        metadata.wSize = C.sizeof(PCO_METADATA_STRUCT)
        timestamp = PCO_TIMESTAMP_STRUCT()
        timestamp.wSize = C.sizeof(PCO_TIMESTAMP_STRUCT)

        # Logging disabled
        # start_time = time.time()
        error = self.PCO_Recorder.PCO_RecorderCopyImage(self.recorder_handle,
                                                        self.camera_handle,
                                                        index,
                                                        x0,
                                                        y0,
                                                        x1,
                                                        y1,
                                                        p_wImgBuf,
                                                        dwImgNumber,
                                                        metadata,
                                                        timestamp)

        ret = {}
        if error == 0:
            ret.update({'version': metadata.wVersion})
            ret.update({'serial number': metadata.dwCAMERA_SERIAL_NO})
            ret.update({'recorder image number': dwImgNumber.value})
            ret.update({'camera image number': timestamp.dwImgCounter})
            ret.update({'wIMAGE_SIZE_X': metadata.wIMAGE_SIZE_X})
            ret.update({'wIMAGE_SIZE_Y': metadata.wIMAGE_SIZE_Y})
            ret.update({'bBINNING_X': metadata.bBINNING_X})
            ret.update({'bBINNING_Y': metadata.bBINNING_Y})
            ret.update({'conversion factor': metadata.wSENSOR_CONV_FACTOR})
            ret.update({'pixel clock': metadata.dwSENSOR_READOUT_FREQUENCY})
            ret.update({'sensor temperature': metadata.sSENSOR_TEMPERATURE})


            ret.update({'image': image})

        # Logging disabled
        # self.log(sys._getframe().f_code.co_name, error, ret, start_time=start_time)
        if error:
            print('Did you wait for the first image in buffer?')
            raise self.exception(sys._getframe().f_code.co_name, error)
        return ret

    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------
    def copy_average_image(self, start, stop, x0, y0, x1, y1):
        """
        """
        self.PCO_Recorder.PCO_RecorderCopyAverageImage.argtypes = [C.c_void_p,
                                                                   C.c_void_p,
                                                                   C.c_uint32,
                                                                   C.c_uint32,
                                                                   C.c_uint16,
                                                                   C.c_uint16,
                                                                   C.c_uint16,
                                                                   C.c_uint16,
                                                                   C.POINTER(C.c_uint16)]

        image = (C.c_uint16 * (((x1-x0)+1)*((y1-y0)+1)))()
        p_wImgBuf = C.cast(image, C.POINTER(C.c_uint16))
        dwStartIdx = C.c_uint32(start)
        dwStopIdx = C.c_uint32(stop)
        wRoiX0 = C.c_uint16(x0)
        wRoiY0 = C.c_uint16(y0)
        wRoiX1 = C.c_uint16(x1)
        wRoiY1 = C.c_uint16(y1)

        # Logging disabled
        # start_time = time.time()
        error = self.PCO_Recorder.PCO_RecorderCopyAverageImage(self.recorder_handle,
                                                               self.camera_handle,
                                                               dwStartIdx,
                                                               dwStopIdx,
                                                               wRoiX0,
                                                               wRoiY0,
                                                               wRoiX1,
                                                               wRoiY1,
                                                               p_wImgBuf)

        ret = {}
        if error == 0:
            ret.update({'average image': image})

        # Logging disabled
        # self.log(sys._getframe().f_code.co_name, error, ret, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)
        return ret




    # -------------------------------------------------------------------------
    # 2.14 PCO_RecorderCopyImageCompressed
    # -------------------------------------------------------------------------
    def copy_image_compressed(self, index, x0, y0, x1, y1):
        """
        """

        class PCO_METADATA_STRUCT(C.Structure):
            _pack_ = 1
            _fields_ = [
                ("wSize", C.c_uint16),
                ("wVersion", C.c_uint16),
                ("bIMAGE_COUNTER_BCD", C.c_uint8 * 4),
                ("bIMAGE_TIME_US_BCD", C.c_uint8 * 3),
                ("bIMAGE_TIME_SEC_BCD", C.c_uint8),
                ("bIMAGE_TIME_MIN_BCD", C.c_uint8),
                ("bIMAGE_TIME_HOUR_BCD", C.c_uint8),
                ("bIMAGE_TIME_DAY_BCD", C.c_uint8),
                ("bIMAGE_TIME_MON_BCD", C.c_uint8),
                ("bIMAGE_TIME_YEAR_BCD", C.c_uint8),
                ("bIMAGE_TIME_STATUS", C.c_uint8),
                ("wEXPOSURE_TIME_BASE", C.c_uint16),
                ("dwEXPOSURE_TIME", C.c_uint32),
                ("dwFRAMERATE_MILLIHZ", C.c_uint32),
                ("sSENSOR_TEMPERATURE", C.c_short),
                ("wIMAGE_SIZE_X", C.c_uint16),
                ("wIMAGE_SIZE_Y", C.c_uint16),
                ("bBINNING_X", C.c_uint8),
                ("bBINNING_Y", C.c_uint8),
                ("dwSENSOR_READOUT_FREQUENCY", C.c_uint32),
                ("wSENSOR_CONV_FACTOR", C.c_uint16),
                ("dwCAMERA_SERIAL_NO", C.c_uint32),
                ("wCAMERA_TYPE", C.c_uint16),
                ("bBIT_RESOLUTION", C.c_uint8),
                ("bSYNC_STATUS", C.c_uint8),
                ("wDARK_OFFSET", C.c_uint16),
                ("bTRIGGER_MODE", C.c_uint8),
                ("bDOUBLE_IMAGE_MODE", C.c_uint8),
                ("bCAMERA_SYNC_MODE", C.c_uint8),
                ("bIMAGE_TYPE", C.c_uint8),
                ("wCOLOR_PATTERN", C.c_uint16)]

        class PCO_TIMESTAMP_STRUCT(C.Structure):
            _pack_ = 1
            _fields_ = [
                ("wSize", C.c_uint16),
                ("dwImgCounter", C.c_uint32),
                ("wYear", C.c_uint16),
                ("wMonth", C.c_uint16),
                ("wDay", C.c_uint16),
                ("wHour", C.c_uint16),
                ("wMinute", C.c_uint16),
                ("wSecond", C.c_uint16),
                ("dwMicroSeconds", C.c_uint32)]

        self.PCO_Recorder.PCO_RecorderCopyImage.argtypes = [C.c_void_p,
                                                            C.c_void_p,
                                                            C.c_uint32,
                                                            C.c_uint16,
                                                            C.c_uint16,
                                                            C.c_uint16,
                                                            C.c_uint16,
                                                            C.POINTER(C.c_uint16),
                                                            C.POINTER(C.c_uint32),
                                                            C.POINTER(PCO_METADATA_STRUCT),
                                                            C.POINTER(PCO_TIMESTAMP_STRUCT)]

        image = (C.c_uint8 * (((x1-x0)+1)*((y1-y0)+1)))()
        p_wImgBuf = C.cast(image, C.POINTER(C.c_uint16))
        dwImgNumber = C.c_uint32()
        metadata = PCO_METADATA_STRUCT()
        metadata.wSize = C.sizeof(PCO_METADATA_STRUCT)
        timestamp = PCO_TIMESTAMP_STRUCT()
        timestamp.wSize = C.sizeof(PCO_TIMESTAMP_STRUCT)

        # Logging disabled
        # start_time = time.time()
        error = self.PCO_Recorder.PCO_RecorderCopyImageCompressed(self.recorder_handle,
                                                        self.camera_handle,
                                                        index,
                                                        x0,
                                                        y0,
                                                        x1,
                                                        y1,
                                                        p_wImgBuf,
                                                        dwImgNumber,
                                                        metadata,
                                                        timestamp)

        ret = {}
        if error == 0:
            ret.update({'version': metadata.wVersion})
            ret.update({'serial number': metadata.dwCAMERA_SERIAL_NO})
            ret.update({'recorder image number': dwImgNumber.value})
            ret.update({'camera image number': timestamp.dwImgCounter})
            ret.update({'wIMAGE_SIZE_X': metadata.wIMAGE_SIZE_X})
            ret.update({'wIMAGE_SIZE_Y': metadata.wIMAGE_SIZE_Y})
            ret.update({'bBINNING_X': metadata.bBINNING_X})
            ret.update({'bBINNING_Y': metadata.bBINNING_Y})
            ret.update({'image': image})

        # Logging disabled
        # self.log(sys._getframe().f_code.co_name, error, ret, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)
        return ret
