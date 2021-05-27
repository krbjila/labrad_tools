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


class sdk:

    """
        This class provides the basic methods for using pco cameras.
    """

    # -------------------------------------------------------------------------
    class exception(Exception):
        def __str__(self):
            return ("Exception: {0} {1:08x}".format(self.args[0],
                                                    self.args[1] & (2**32-1)))

    # -------------------------------------------------------------------------
    def __init__(self, debuglevel='off', timestamp='off', name=''):

        if platform.architecture()[0] != '64bit':
            print('Python Interpreter not x64')
            raise OSError

        self.__dll_name = 'SC2_Cam.dll'
        dll_path = os.path.dirname(__file__).replace('\\', '/')

        try:
            self.SC2_Cam = C.windll.LoadLibrary(dll_path + '/' + self.__dll_name)
        except OSError:
            print('Error: ' + '"' + self.__dll_name + '" not found in directory "' + dll_path + '".')
            raise

        self.camera_handle = C.c_void_p(0)
        self.lens_control = C.c_void_p(0)

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
            print(ts + '[' + self.name +']' + '[sdk] ' + name + ':', self.get_error_text(error))
        elif self.debuglevel == 'verbose':
            print(ts + '[' + self.name +']' + '[sdk] ' + name + ':', self.get_error_text(error))
        elif self.debuglevel == 'extra verbose':
            print(ts + '[' + self.name +']' + '[sdk] ' + name + ':', self.get_error_text(error))
            if data is not None:
                for key, value in data.items():
                    print('   -', key + ':', value)

    # ---------------------------------------------------------------------
    def get_error_text(self, errorcode):
        """
        """

        self.SC2_Cam.PCO_GetErrorText.argtypes = [C.c_uint32,
                                                  C.POINTER(C.c_uint32),
                                                  C.c_uint32]

        buffer = (C.c_char * 500)()
        p_buffer = C.cast(buffer, C.POINTER(C.c_ulong))

        self.SC2_Cam.PCO_GetErrorText(errorcode, p_buffer, 500)

        temp_list = []
        for i in range(100):
            temp_list.append(buffer[i])
        output_string = bytes.join(b'', temp_list).decode('ascii')

        return output_string.strip("\0")

    # ---------------------------------------------------------------------
    def get_camera_handle(self):
        return self.camera_handle

    # ---------------------------------------------------------------------
    # 2.1.1 PCO_OpenCamera
    # ---------------------------------------------------------------------
    def open_camera(self):
        """
        This function is used to get a connection to a camera. This function
        scans through all available interfaces and tries to connect to the next
        available camera.
        """

        self.SC2_Cam.PCO_OpenCamera.argtypes = [C.POINTER(C.c_void_p),
                                                C.c_uint16]

        start_time = time.time()
        error = self.SC2_Cam.PCO_OpenCamera(self.camera_handle, 0)

        ret = {}
        ret.update({'camera handle': self.camera_handle})

        self.log(sys._getframe().f_code.co_name, error, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)
        return ret

    # -------------------------------------------------------------------------
    # 2.1.2 PCO_OpenCameraEx
    # -------------------------------------------------------------------------
    def open_camera_ex(self, interface, camera_number=0):
        """
        This function is used to get a connection to a specific camera.
        """

        class PCO_OPEN_STRUCT(C.Structure):
            _pack_ = 1
            _fields_ = [
                ("wSize", C.c_uint16),
                ("wInterfaceType", C.c_uint16),
                ("wCameraNumber", C.c_uint16),
                ("wCameraNumAtInterface", C.c_uint16),
                ("wOpenFlags", C.c_uint16 * 10),
                ("dwOpenFlags", C.c_uint32 * 5),
                ("wOpenPtr", C.c_void_p * 6),
                ("zzwDummy", C.c_uint16 * 8)]

        self.SC2_Cam.PCO_OpenCameraEx.argtypes = [C.POINTER(C.c_void_p),
                                                  PCO_OPEN_STRUCT]

        interface_dict = {'FireWire': 1,
                          'GigE': 5,
                          'USB 2.0': 6,
                          'Camera Link Silicon Software': 7,
                          'USB 3.0': 8,
                          'CLHS': 11}

        strOpenStruct = PCO_OPEN_STRUCT()
        strOpenStruct.wSize = C.sizeof(PCO_OPEN_STRUCT)
        strOpenStruct.wInterfaceType = interface_dict[interface]
        strOpenStruct.wCameraNumber = camera_number
        strOpenStruct.wCameraNumAtInterface = 0
        strOpenStruct.wOpenFlags[0] = 0x0000
        strOpenStruct.wOpenFlags[1] = 0x0000
        strOpenStruct.wOpenFlags[2] = 0x0000
        strOpenStruct.dwOpenFlags[0] = 0x00000000
        strOpenStruct.dwOpenFlags[1] = 0x00000000
        strOpenStruct.dwOpenFlags[2] = 0x00000000
        strOpenStruct.dwOpenFlags[3] = 0x00000000
        strOpenStruct.dwOpenFlags[4] = 0x00000000
        strOpenStruct.wOpenPtr[0] = 0
        strOpenStruct.wOpenPtr[1] = 0
        strOpenStruct.wOpenPtr[2] = 0
        strOpenStruct.wOpenPtr[3] = 0
        strOpenStruct.wOpenPtr[4] = 0
        strOpenStruct.wOpenPtr[5] = 0

        start_time = time.time()
        error = self.SC2_Cam.PCO_OpenCameraEx(self.camera_handle, strOpenStruct)

        self.log(sys._getframe().f_code.co_name, error, start_time=start_time)

        return {'error': error}

    # -------------------------------------------------------------------------
    # 2.1.3 PCO_CloseCamera
    # -------------------------------------------------------------------------
    def close_camera(self):
        """
        This function is used to close the connection to a previously opened
        camera.
        """

        self.SC2_Cam.PCO_CloseCamera.argtypes = [C.c_void_p]

        start_time = time.time()
        error = self.SC2_Cam.PCO_CloseCamera(self.camera_handle)

        self.log(sys._getframe().f_code.co_name, error, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)

    # -------------------------------------------------------------------------
    # 2.1.4 PCO_ResetLib
    # -------------------------------------------------------------------------
    def reset_lib(self):
        """
        This function is used to set the sc2_cam library to an initial state.
        All camera handles have to be closed with close_camera before this
        function is called.
        """

        self.SC2_Cam.PCO_ResetLib.argtypes = [C.POINTER(C.c_void_p)]

        start_time = time.time()
        error = self.SC2_Cam.PCO_ResetLib(self.camera_handle)

        self.log(sys._getframe().f_code.co_name, error, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)

    # -------------------------------------------------------------------------
    # 2.1.5 PCO_CheckDeviceAvailability (for the moment intentionally not implemented)
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # 2.2.1 PCO_GetCameraDescription
    # -------------------------------------------------------------------------
    def get_camera_description(self):
        """
        Sensor and camera specific description is queried.

        :return: camera description
        :rtype: dict
        """
        class PCO_Description(C.Structure):
            _pack_ = 1
            _fields_ = [
                ("wSize", C.c_uint16),
                ("wSensorTypeDESC", C.c_uint16),
                ("wSensorSubTypeDESC", C.c_uint16),
                ("wMaxHorzResStdDESC", C.c_uint16),
                ("wMaxVertResStdDESC", C.c_uint16),
                ("wMaxHorzResExtDESC", C.c_uint16),
                ("wMaxVertResExtDESC", C.c_uint16),
                ("wDynResDESC", C.c_uint16),
                ("wMaxBinHorzDESC", C.c_uint16),
                ("wBinHorzSteppingDESC", C.c_uint16),
                ("wMaxBinVertDESC", C.c_uint16),
                ("wBinVertSteppingDESC", C.c_uint16),
                ("wRoiHorStepsDESC", C.c_uint16),
                ("wRoiVertStepsDESC", C.c_uint16),
                ("wNumADCsDESC", C.c_uint16),
                ("wMinSizeHorzDESC", C.c_uint16),
                ("dwPixelRateDESC", C.c_uint32 * 4),
                ("ZZdwDummypr", C.c_uint32 * 20),
                ("wConvFactDESC", C.c_uint16 * 4),
                ("sCoolingSetpoints", C.c_short * 10),
                ("ZZdwDummycv", C.c_uint16 * 8),
                ("wSoftRoiHorStepsDESC", C.c_uint16),
                ("wSoftRoiVertStepsDESC", C.c_uint16),
                ("wIRDESC", C.c_uint16),
                ("wMinSizeVertDESC", C.c_uint16),
                ("dwMinDelayDESC", C.c_uint32),
                ("dwMaxDelayDESC", C.c_uint32),
                ("dwMinDelayStepDESC", C.c_uint32),
                ("dwMinExposDESC", C.c_uint32),
                ("dwMaxExposDESC", C.c_uint32),
                ("dwMinExposStepDESC", C.c_uint32),
                ("dwMinDelayIRDESC", C.c_uint32),
                ("dwMaxDelayIRDESC", C.c_uint32),
                ("dwMinExposIRDESC", C.c_uint32),
                ("dwMaxExposIRDESC", C.c_uint32),
                ("wTimeTableDESC", C.c_uint16),
                ("wDoubleImageDESC", C.c_uint16),
                ("sMinCoolSetDESC", C.c_short),
                ("sMaxCoolSetDESC", C.c_short),
                ("sDefaultCoolSetDESC", C.c_short),
                ("wPowerDownModeDESC", C.c_uint16),
                ("wOffsetRegulationDESC", C.c_uint16),
                ("wColorPatternDESC", C.c_uint16),
                ("wPatternTypeDESC", C.c_uint16),
                ("wDummy1", C.c_uint16),
                ("wDummy2", C.c_uint16),
                ("wNumCoolingSetpoints", C.c_uint16),
                ("dwGeneralCapsDESC1", C.c_uint32),
                ("dwGeneralCapsDESC2", C.c_uint32),
                ("dwExtSyncFrequency", C.c_uint32 * 4),
                ("dwGeneralCapsDESC3", C.c_uint32),
                ("dwGeneralCapsDESC4", C.c_uint32),
                ("ZzdwDummy", C.c_uint32)]

        self.SC2_Cam.PCO_GetCameraDescription.argtypes = [C.c_void_p,
                                                          C.POINTER(PCO_Description)]

        strDescription = PCO_Description()
        strDescription.wSize = C.sizeof(PCO_Description)

        start_time = time.time()
        error = self.SC2_Cam.PCO_GetCameraDescription(self.camera_handle,
                                                      strDescription)

        ret = {}
        ret.update({'sensor type': strDescription.wSensorTypeDESC})
        ret.update({'sensor subtype': strDescription.wSensorSubTypeDESC})
        ret.update({'max. horizontal resolution standard': strDescription.wMaxHorzResStdDESC})
        ret.update({'max. vertical resolution standard': strDescription.wMaxVertResStdDESC})
        ret.update({'max. horizontal resolution extended': strDescription.wMaxHorzResExtDESC})
        ret.update({'max. vertical resolution extended': strDescription.wMaxVertResExtDESC})
        ret.update({'dynamic': strDescription.wDynResDESC})
        ret.update({'max. binning horizontal': strDescription.wMaxBinHorzDESC})
        ret.update({'binning horizontal stepping': strDescription.wBinHorzSteppingDESC})
        ret.update({'max. binning vert': strDescription.wMaxBinVertDESC})
        ret.update({'binning vert stepping': strDescription.wBinVertSteppingDESC})
        ret.update({'roi hor steps': strDescription.wRoiHorStepsDESC})
        ret.update({'roi vert steps': strDescription.wRoiVertStepsDESC})
        ret.update({'number adcs': strDescription.wNumADCsDESC})
        ret.update({'min size horz': strDescription.wMinSizeHorzDESC})

        prtuple = (strDescription.dwPixelRateDESC[0],
                   strDescription.dwPixelRateDESC[1],
                   strDescription.dwPixelRateDESC[2],
                   strDescription.dwPixelRateDESC[3])

        ret.update({'pixel rate': list(prtuple)})

        cftuple = (strDescription.wConvFactDESC[0],
                   strDescription.wConvFactDESC[1],
                   strDescription.wConvFactDESC[2],
                   strDescription.wConvFactDESC[3])

        ret.update({'conversion factor': list(cftuple)})

        cstuple = (strDescription.sCoolingSetpoints[0],
                   strDescription.sCoolingSetpoints[1],
                   strDescription.sCoolingSetpoints[2],
                   strDescription.sCoolingSetpoints[3],
                   strDescription.sCoolingSetpoints[4],
                   strDescription.sCoolingSetpoints[5],
                   strDescription.sCoolingSetpoints[6],
                   strDescription.sCoolingSetpoints[7],
                   strDescription.sCoolingSetpoints[8],
                   strDescription.sCoolingSetpoints[9])

        ret.update({'cooling setpoints': list(cstuple)})

        ret.update({'soft roi hor steps': strDescription.wSoftRoiHorStepsDESC})
        ret.update({'soft roi vert steps': strDescription.wSoftRoiVertStepsDESC})
        ret.update({'ir': strDescription.wIRDESC})
        ret.update({'min size vert': strDescription.wMinSizeVertDESC})
        ret.update({'Min Delay DESC': strDescription.dwMinDelayDESC})
        ret.update({'Max Delay DESC': strDescription.dwMaxDelayDESC})
        ret.update({'Min Delay StepDESC': strDescription.dwMinDelayStepDESC})
        ret.update({'Min Expos DESC': strDescription.dwMinExposDESC})
        ret.update({'Max Expos DESC': strDescription.dwMaxExposDESC})
        ret.update({'Min Expos Step DESC': strDescription.dwMinExposStepDESC})
        ret.update({'Min Delay IR DESC': strDescription.dwMinDelayIRDESC})
        ret.update({'Max Delay IR DESC': strDescription.dwMaxDelayIRDESC})
        ret.update({'Min Expos IR DESC': strDescription.dwMinExposIRDESC})
        ret.update({'Max ExposIR DESC': strDescription.dwMaxExposIRDESC})
        ret.update({'Time Table DESC': strDescription.wTimeTableDESC})
        ret.update({'wDoubleImageDESC': strDescription.wDoubleImageDESC})
        ret.update({'Min Cool Set DESC': strDescription.sMinCoolSetDESC})
        ret.update({'Max Cool Set DESC': strDescription.sMaxCoolSetDESC})
        ret.update({'Default Cool Set DESC': strDescription.sDefaultCoolSetDESC})
        ret.update({'Power Down Mode DESC': strDescription.wPowerDownModeDESC})
        ret.update({'Offset Regulation DESC': strDescription.wOffsetRegulationDESC})
        ret.update({'Color Pattern DESC': strDescription.wColorPatternDESC})
        ret.update({'Pattern Type DESC': strDescription.wPatternTypeDESC})
        ret.update({'Num Cooling Setpoints': strDescription.wNumCoolingSetpoints})
        ret.update({'dwGeneralCapsDESC1': strDescription.dwGeneralCapsDESC1})
        ret.update({'dwGeneralCapsDESC2': strDescription.dwGeneralCapsDESC2})

        efstuple = (strDescription.dwExtSyncFrequency[0],
                    strDescription.dwExtSyncFrequency[1],
                    strDescription.dwExtSyncFrequency[2],
                    strDescription.dwExtSyncFrequency[3])

        ret.update({'ext sync frequency': list(efstuple)})

        ret.update({'dwGeneralCapsDESC3': strDescription.dwGeneralCapsDESC3})
        ret.update({'dwGeneralCapsDESC4': strDescription.dwGeneralCapsDESC4})

        self.log(sys._getframe().f_code.co_name, error, ret, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)
        return ret

    # -------------------------------------------------------------------------
    # 2.2.2 PCO_GetCameraDescriptionEx
    # -------------------------------------------------------------------------
    def get_camera_description_ex(self, description_type):
        """
        """
        class PCO_Description(C.Structure):
            _pack_ = 1
            _fields_ = [
                ("wSize", C.c_uint16),
                ("wSensorTypeDESC", C.c_uint16),
                ("wSensorSubTypeDESC", C.c_uint16),
                ("wMaxHorzResStdDESC", C.c_uint16),
                ("wMaxVertResStdDESC", C.c_uint16),
                ("wMaxHorzResExtDESC", C.c_uint16),
                ("wMaxVertResExtDESC", C.c_uint16),
                ("wDynResDESC", C.c_uint16),
                ("wMaxBinHorzDESC", C.c_uint16),
                ("wBinHorzSteppingDESC", C.c_uint16),
                ("wMaxBinVertDESC", C.c_uint16),
                ("wBinVertSteppingDESC", C.c_uint16),
                ("wRoiHorStepsDESC", C.c_uint16),
                ("wRoiVertStepsDESC", C.c_uint16),
                ("wNumADCsDESC", C.c_uint16),
                ("wMinSizeHorzDESC", C.c_uint16),
                ("dwPixelRateDESC", C.c_uint32 * 4),
                ("ZZdwDummypr", C.c_uint32 * 20),
                ("wConvFactDESC", C.c_uint16 * 4),
                ("sCoolingSetpoints", C.c_short * 10),
                ("ZZdwDummycv", C.c_uint16 * 8),
                ("wSoftRoiHorStepsDESC", C.c_uint16),
                ("wSoftRoiVertStepsDESC", C.c_uint16),
                ("wIRDESC", C.c_uint16),
                ("wMinSizeVertDESC", C.c_uint16),
                ("dwMinDelayDESC", C.c_uint32),
                ("dwMaxDelayDESC", C.c_uint32),
                ("dwMinDelayStepDESC", C.c_uint32),
                ("dwMinExposDESC", C.c_uint32),
                ("dwMaxExposDESC", C.c_uint32),
                ("dwMinExposStepDESC", C.c_uint32),
                ("dwMinDelayIRDESC", C.c_uint32),
                ("dwMaxDelayIRDESC", C.c_uint32),
                ("dwMinExposIRDESC", C.c_uint32),
                ("dwMaxExposIRDESC", C.c_uint32),
                ("wTimeTableDESC", C.c_uint16),
                ("wDoubleImageDESC", C.c_uint16),
                ("sMinCoolSetDESC", C.c_short),
                ("sMaxCoolSetDESC", C.c_short),
                ("sDefaultCoolSetDESC", C.c_short),
                ("wPowerDownModeDESC", C.c_uint16),
                ("wOffsetRegulationDESC", C.c_uint16),
                ("wColorPatternDESC", C.c_uint16),
                ("wPatternTypeDESC", C.c_uint16),
                ("wDummy1", C.c_uint16),
                ("wDummy2", C.c_uint16),
                ("wNumCoolingSetpoints", C.c_uint16),
                ("dwGeneralCapsDESC1", C.c_uint32),
                ("dwGeneralCapsDESC2", C.c_uint32),
                ("dwExtSyncFrequency", C.c_uint32 * 4),
                ("dwGeneralCapsDESC3", C.c_uint32),
                ("dwGeneralCapsDESC4", C.c_uint32),
                ("ZzdwDummy", C.c_uint32)]

        class PCO_Description_2(C.Structure):
            _pack_ = 1
            _fields_ = [
                ("wSize", C.c_uint16),
                ("ZZwAlignDummy1", C.c_uint16),
                ("dwMinPeriodicalTimeDESC2", C.c_uint32),
                ("dwMaxPeriodicalTimeDESC2", C.c_uint32),
                ("dwMinPeriodicalConditionDESC2", C.c_uint32),
                ("dwMaxNumberOfExposuresDESC2", C.c_uint32),
                ("lMinMonitorSignalOffsetDESC2", C.c_long),
                ("dwMaxMonitorSignalOffsetDESC2", C.c_uint32),
                ("dwMinPeriodicalStepDESC2", C.c_uint32),
                ("dwStartTimeDelayDESC2", C.c_uint32),
                ("dwMinMonitorStepDESC2", C.c_uint32),
                ("dwMinDelayModDESC2", C.c_uint32),
                ("dwMaxDelayModDESC2", C.c_uint32),
                ("dwMinDelayStepModDESC2", C.c_uint32),
                ("dwMinExposureModDESC2", C.c_uint32),
                ("dwMaxExposureModDESC2", C.c_uint32),
                ("dwMinExposureStepModDESC2", C.c_uint32),
                ("dwModulateCapsDESC2", C.c_uint32),
                ("dwReserved", C.c_uint32 * 16),
                ("ZZdwDummy", C.c_uint32 * 41)]

        desc = {'PCO_DESCRIPTION': 0, 'PCO_DESCRIPTION_2': 1}
        wType = C.c_uint16(desc[description_type])

        if description_type == 'PCO_DESCRIPTION':
            self.SC2_Cam.PCO_GetCameraDescriptionEx.argtypes = [C.c_void_p,
                                                                C.POINTER(PCO_Description),
                                                                C.c_uint16]
            strDescEx = PCO_Description()
            strDescEx.wSize = C.sizeof(PCO_Description)

        elif description_type == 'PCO_DESCRIPTION_2':
            self.SC2_Cam.PCO_GetCameraDescriptionEx.argtypes = [C.c_void_p,
                                                                C.POINTER(PCO_Description_2),
                                                                C.c_uint16]
            strDescEx = PCO_Description_2()
            strDescEx.wSize = C.sizeof(PCO_Description_2)

        start_time = time.time()
        error = self.SC2_Cam.PCO_GetCameraDescriptionEx(self.camera_handle,
                                                        strDescEx,
                                                        wType)

        ret = {}
        ret.update({'___': 1})

        self.log(sys._getframe().f_code.co_name, error, ret, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)
        return ret

    # -------------------------------------------------------------------------
    # 2.3.1 PCO_GetGeneral (for the moment intentionally not implemented)
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # 2.3.2 PCO_GetCameraType
    # -------------------------------------------------------------------------
    def get_camera_type(self):
        """
        This function retrieves the camera type code, hardware/firmware
        version, serial number and interface type of the camera.

        :return: {'camera type': str,
                'camera subtype': str,
                'serial number': int,
                'interface type': str}
        :rtype: dict
        """
        class PCO_SC2_Hardware_DESC(C.Structure):
            _pack_ = 1
            _fields_ = [
                ("szName", C.c_char * 16),
                ("wBatchNo", C.c_uint16),
                ("wRevision", C.c_uint16),
                ("wVariant", C.c_uint16),
                ("ZZwDummy", C.c_uint16 * 20)]

        class PCO_SC2_Firmware_DESC(C.Structure):
            _pack_ = 1
            _fields_ = [
                ("szName", C.c_char * 16),
                ("bMinorRev", C.c_uint8),
                ("bMajorRev", C.c_uint8),
                ("wVariant", C.c_uint16),
                ("ZZwDummy", C.c_uint16 * 22)]

        class PCO_HW_Vers(C.Structure):
            _pack_ = 1
            _fields_ = [
                ("BoardNum", C.c_uint16),
                ("Board", PCO_SC2_Hardware_DESC * 10)]

        class PCO_FW_Vers(C.Structure):
            _pack_ = 1
            _fields_ = [
                ("DeviceNum", C.c_uint16),
                ("Device", PCO_SC2_Firmware_DESC * 10)]

        class PCO_CameraType(C.Structure):
            _pack_ = 1
            _fields_ = [
                ("wSize", C.c_uint16),
                ("wCamType", C.c_uint16),
                ("wCamSubType", C.c_uint16),
                ("ZZwAlignDummy1", C.c_uint16),
                ("dwSerialNumber", C.c_uint32),
                ("dwHWVersion", C.c_uint32),
                ("dwFWVersion", C.c_uint32),
                ("wInterfaceType", C.c_uint16),
                ("strHardwareVersion", PCO_HW_Vers),
                ("strFirmwareVersion", PCO_FW_Vers),
                ("ZZwDummy", C.c_uint16 * 39)]

        self.SC2_Cam.PCO_GetCameraType.argtypes = [C.c_void_p,
                                                   C.POINTER(PCO_CameraType)]

        strCamType = PCO_CameraType()
        strCamType.wSize = C.sizeof(PCO_CameraType)

        start_time = time.time()
        error = self.SC2_Cam.PCO_GetCameraType(self.camera_handle,
                                               strCamType)

        ret = {}
        if error == 0:
            camera_type = {0x0100: 'pco.1200HS',
                           0x0200: 'pco.1300',
                           0x0220: 'pco.1600',
                           0x0240: 'pco.2000',
                           0x0260: 'pco.4000',
                           0x0830: 'pco.1400',
                           0x1000: 'pco.dimax',
                           0x1010: 'pco.dimax_TV',
                           0x1020: 'pco.dimax CS',
                           0x1400: 'pco.flim',
                           0x1600: 'pco.panda',
                           0x0800: 'pco.pixelfly usb',
                           0x1300: 'pco.edge 5.5 CL',
                           0x1302: 'pco.edge 4.2 CL',
                           0x1310: 'pco.edge GL',
                           0x1320: 'pco.edge USB3',
                           0x1340: 'pco.edge CLHS',
                           0x1304: 'pco.edge MT',
                           0x1800: 'pco.edge family'}

            interface_type = {0x0001: 'FireWire',
                              0x0002: 'Camera Link',
                              0x0003: 'USB 2.0',
                              0x0004: 'GigE',
                              0x0005: 'Serial Interface',
                              0x0006: 'USB 3.0',
                              0x0007: 'CLHS',
                              0x0009: 'USB 3.1 Gen 1'}

            ret.update({'camera type': camera_type.get(strCamType.wCamType, strCamType.wCamType)})
            ret.update({'camera subtype': strCamType.wCamSubType})
            ret.update({'serial number': strCamType.dwSerialNumber})
            ret.update({'interface type': interface_type.get(strCamType.wInterfaceType, strCamType.wInterfaceType)})

        self.log(sys._getframe().f_code.co_name, error, ret, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)
        return ret

    # -------------------------------------------------------------------------
    # 2.3.3 PCO_GetCameraHealthStatus
    # -------------------------------------------------------------------------
    def get_camera_health_status(self):
        """
        This function retrieves information about the current camera status.
        It is recommended to call this function frequently (e.g. every 5s or
        after calling arm_camera()) in order to recognize camera internal
        problems. This helps to prevent camera hardware from damage.

        :return: {'warning': int,
                'error': int,
                'status': int}
        :rtype: dict
        """

        self.SC2_Cam.PCO_GetCameraHealthStatus.argtypes = [C.c_void_p,
                                                           C.POINTER(C.c_uint32),
                                                           C.POINTER(C.c_uint32),
                                                           C.POINTER(C.c_uint32)]

        dwWarning = C.c_uint32()
        dwError = C.c_uint32()
        dwStatus = C.c_uint32()

        start_time = time.time()
        error = self.SC2_Cam.PCO_GetCameraHealthStatus(self.camera_handle,
                                                       dwWarning,
                                                       dwError,
                                                       dwStatus)

        ret = {}
        if error == 0:
            ret.update({'warning': dwWarning.value})
            ret.update({'error': dwError.value})
            ret.update({'status': dwStatus.value})

        self.log(sys._getframe().f_code.co_name, error, ret, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)
        return ret

    # -------------------------------------------------------------------------
    # 2.3.4 PCO_GetTemperature
    # -------------------------------------------------------------------------
    def get_temperature(self):
        """
        This function retrieves the current temperatures in °C of the imaging
        sensor, camera and additional devices e.g. power supply.

        :return: {'sensor temperature': float,
                'camera temperature': float,
                'power temperature': float}

        :rtype: dict
        """
        start_time = time.time()

        self.SC2_Cam.PCO_GetTemperature.argtypes = [C.c_void_p,
                                                    C.POINTER(C.c_short),
                                                    C.POINTER(C.c_short),
                                                    C.POINTER(C.c_short)]

        sCCDTemp, sCamTemp, sPowTemp = (C.c_short(), C.c_short(), C.c_short())

        start_time = time.time()
        error = self.SC2_Cam.PCO_GetTemperature(self.camera_handle,
                                                sCCDTemp,
                                                sCamTemp,
                                                sPowTemp)

        ret = {}
        if error == 0:
            ret.update({'sensor temperature': float((sCCDTemp.value)/10.0)})
            ret.update({'camera temperature': float(sCamTemp.value)})
            ret.update({'power temperature': float(sPowTemp.value)})

        self.log(sys._getframe().f_code.co_name, error, ret, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)
        return ret

    # -------------------------------------------------------------------------
    # 2.3.5 PCO_GetInfoString
    # -------------------------------------------------------------------------
    def get_info_string(self, info_type):
        """
        This function retrieves some information about the camera, e.g. sensor
        name.

        :param info_type:
            * INFO_STRING_PCO_INTERFACE, camera name & interface information
            * INFO_STRING_CAMERA, camera name
            * INFO_STRING_SENSOR, sensor name
            * INFO_STRING_PCO_MATERIALNUMBER, production number
            * INFO_STRING_BUILD, firmware build number and date
            * INFO_STRING_PCO_INCLUDE, firmware build include revision

        :return: {'info string': str}
        :rtype: dict

        """

        self.SC2_Cam.PCO_GetInfoString.argtypes = [C.c_void_p,
                                                   C.c_uint32,
                                                   C.POINTER(C.c_char),
                                                   C.c_uint16]

        info = {'INFO_STRING_PCO_INTERFACE': 0,
                'INFO_STRING_CAMERA': 1,
                'INFO_STRING_SENSOR': 2,
                'INFO_STRING_PCO_MATERIALNUMBER': 3,
                'INFO_STRING_BUILD': 4,
                'INFO_STRING_PCO_INCLUDE': 5}

        buffer = (C.c_char * 500)()
        p_buffer = C.cast(buffer, C.POINTER(C.c_char))

        start_time = time.time()
        error = self.SC2_Cam.PCO_GetInfoString(self.camera_handle,
                                               info[info_type],
                                               p_buffer,
                                               500)

        ret = {}
        if error == 0:
            temp_list = []
            for i in range(500):
                temp_list.append(buffer[i])
            output_string = bytes.join(b'', temp_list).decode('ascii')
            ret.update({'info string': output_string.strip("\0")})

        self.log(sys._getframe().f_code.co_name, error, ret, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)
        return ret

    # -------------------------------------------------------------------------
    # 2.3.6 PCO_GetCameraName
    # -------------------------------------------------------------------------
    def get_camera_name(self):
        """
        This function retrieves the name of the camera.

        :return: {'camera name': str}
        :rtype: dict

        >>> get_camera_name()
        {'camera name': 'pco.edge 5.5 M CLHS'}

        """

        self.SC2_Cam.PCO_GetCameraName.argtypes = [C.c_void_p,
                                                   C.POINTER(C.c_char),
                                                   C.c_uint32]

        buffer = (C.c_char * 40)()
        p_buffer = C.cast(buffer, C.POINTER(C.c_char))

        start_time = time.time()
        error = self.SC2_Cam.PCO_GetCameraName(self.camera_handle,
                                               p_buffer,
                                               40)

        ret = {}
        if error == 0:
            temp_list = []
            for i in range(40):
                temp_list.append(buffer[i])
            output_string = bytes.join(b'', temp_list).decode('ascii')
            ret.update({'camera name': output_string.strip("\0")})

        self.log(sys._getframe().f_code.co_name, error, ret, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)
        return ret

    # -------------------------------------------------------------------------
    # 2.3.7 PCO_GetFirmwareInfo
    # -------------------------------------------------------------------------
    def get_firmware_info(self, device):
        """
        Query firmware versions of all devices in the camera such as main
        microprocessor, main FPGA and coprocessors of the interface boards.

        :return: {'device 0 name': str,
                'device 0 major': int,
                'device 0 minor': int,
                'device 0 variant': int}
        :rtype: dict
        """
        class PCO_SC2_Firmware_DESC(C.Structure):
            _pack_ = 1
            _fields_ = [
                ("szName", C.c_char * 16),
                ("bMinorRev", C.c_uint8),
                ("bMajorRev", C.c_uint8),
                ("wVariant", C.c_uint16),
                ("ZZwDummy", C.c_uint16 * 22)]

        class PCO_FW_Vers(C.Structure):
            _pack_ = 1
            _fields_ = [
                ("DeviceNum", C.c_uint16),
                ("Device", PCO_SC2_Firmware_DESC * 10)]

        self.SC2_Cam.PCO_GetFirmwareInfo.argtypes = [C.c_void_p,
                                                     C.c_uint16,
                                                     C.POINTER(PCO_FW_Vers)]

        pstrFirmWareVersion = PCO_FW_Vers()
        deviceX = C.c_uint16(device)

        start_time = time.time()
        error = self.SC2_Cam.PCO_GetFirmwareInfo(self.camera_handle,
                                                 deviceX,
                                                 pstrFirmWareVersion)

        ret = {}
        if error == 0:
            ret.update({'name': pstrFirmWareVersion.Device[0].szName.decode('ascii')})
            ret.update({'major': pstrFirmWareVersion.Device[0].bMajorRev})
            ret.update({'minor': pstrFirmWareVersion.Device[0].bMinorRev})
            ret.update({'variant': pstrFirmWareVersion.Device[0].wVariant})

        self.log(sys._getframe().f_code.co_name, error, ret, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)
        return ret

    # -------------------------------------------------------------------------
    # 2.3.8 PCO_GetColorCorrectionMatrix
    # -------------------------------------------------------------------------
    def get_color_correction_matrix(self):
        """
        This function returns the color multiplier matrix from the camera. The
        color multiplier matrix can be used to normalize the color values of a
        color camera to a color temperature of 6500 K. The color multiplier
        matrix is specific for each camera and is determined through a special
        calibration procedure.

        :return: {'ccm': tuple}
        :rtype: dict
        """

        self.SC2_Cam.PCO_GetColorCorrectionMatrix.argtypes = [C.c_void_p,
                                                              C.POINTER(C.c_double)]

        Matrix = (C.c_double * 9)()
        pdMatrix = C.cast(Matrix, C.POINTER(C.c_double))

        start_time = time.time()
        error = self.SC2_Cam.PCO_GetColorCorrectionMatrix(self.camera_handle,
                                                          pdMatrix)

        ret = {}
        if error == 0:
            mtuple = (Matrix[0],
                      Matrix[1],
                      Matrix[2],
                      Matrix[3],
                      Matrix[4],
                      Matrix[5],
                      Matrix[6],
                      Matrix[7],
                      Matrix[8])
            ret.update({'ccm': list(mtuple)})

        self.log(sys._getframe().f_code.co_name, error, ret, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)
        return ret

    # -------------------------------------------------------------------------
    # 2.4.1 PCO_ArmCamera
    # -------------------------------------------------------------------------
    def arm_camera(self):
        """
        This function arms, this means prepare the camera for a following
        recording. All configurations and settings made up to this moment are
        accepted, validated and the internal settings of the camera are
        prepared. If the arm was successful the camera state is changed to
        [armed] and the camera is able to start image recording immediately,
        when Recording State is set to [run].
        """

        self.SC2_Cam.PCO_ArmCamera.argtypes = [C.c_void_p]

        start_time = time.time()
        error = self.SC2_Cam.PCO_ArmCamera(self.camera_handle)

        self.log(sys._getframe().f_code.co_name, error, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)

    # -------------------------------------------------------------------------
    # 2.4.2 PCO_CamLinkSetImageParameters                            (obsolete)
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # 2.4.3 PCO_SetImageParameter
    # -------------------------------------------------------------------------
    def set_image_parameters(self, image_width, image_height):
        """
        This function sets the image parameters for internal allocated
        resources.
        """

        self.SC2_Cam.PCO_SetImageParameters.argtypes = [C.c_void_p,
                                                        C.c_uint16,
                                                        C.c_uint16,
                                                        C.c_uint32,
                                                        C.c_void_p(),
                                                        C.c_int]

        wxres = C.c_uint16(image_width)
        wyres = C.c_uint16(image_height)
        dwFlags = C.c_uint32(2)
        param = C.c_void_p(0)
        ilen = C.c_int(0)

        start_time = time.time()
        error = self.SC2_Cam.PCO_SetImageParameters(self.camera_handle,
                                                    wxres,
                                                    wyres,
                                                    dwFlags,
                                                    param,
                                                    ilen)

        self.log(sys._getframe().f_code.co_name, error, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)

    # -------------------------------------------------------------------------
    # 2.4.4 PCO_ResetSettingsToDefault
    # -------------------------------------------------------------------------
    def reset_settings_to_default(self):
        """
        This function can be used to reset all camera settings to its default
        values. This function is also executed during a power-up sequence. The
        camera must be stopped before calling this command. Default settings
        are slightly different for all cameras.
        """

        self.SC2_Cam.PCO_ResetSettingsToDefault.argtypes = [C.c_void_p]

        start_time = time.time()
        error = self.SC2_Cam.PCO_ResetSettingsToDefault(self.camera_handle)

        self.log(sys._getframe().f_code.co_name, error, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)

    # -------------------------------------------------------------------------
    # 2.4.5 PCO_SetTimeouts (for the moment intentionally not implemented)
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # 2.4.6 PCO_RebootCamera
    # -------------------------------------------------------------------------
    def reboot_camera(self):
        """
        This function will reboot the camera. The function will return
        immediately and the reboot process in the camera is started. After
        calling this command the handle to this camera should be closed with
        close_camera().
        """

        self.SC2_Cam.PCO_RebootCamera.argtypes = [C.c_void_p]

        start_time = time.time()
        error = self.SC2_Cam.PCO_RebootCamera(self.camera_handle)

        self.log(sys._getframe().f_code.co_name, error, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)

    # -------------------------------------------------------------------------
    # 2.4.7 PCO_GetCameraSetup
    # -------------------------------------------------------------------------
    def get_camera_setup(self):
        """
        This command returns the shutter mode of a pco.edge. This function
        is used to query the current operation mode of the camera. Some cameras
        can work at different operation modes with different descriptor
        settings.


        :rtype: dict
        """

        self.SC2_Cam.PCO_GetCameraSetup.argtypes = [C.c_void_p,
                                                    C.POINTER(C.c_uint16),
                                                    C.POINTER(C.c_uint32),
                                                    C.POINTER(C.c_uint16)]

        wType = C.c_uint16(0)
        dwSetup = (C.c_uint32 * 4)()
        pdwSetup = C.cast(dwSetup[0], C.POINTER(C.c_uint32))
        wLen = C.c_uint16(4)

        dwSetup[0] = 99
        dwSetup[1] = 99
        dwSetup[2] = 99
        dwSetup[3] = 99

        start_time = time.time()
        error = self.SC2_Cam.PCO_GetCameraSetup(self.camera_handle,
                                                wType,
                                                pdwSetup,
                                                wLen)

        ret = {}
        if error == 0:
            ret.update({'type': wType.value,
                        'setup': (dwSetup[0],
                                  dwSetup[1],
                                  dwSetup[2],
                                  dwSetup[3]),
                        'length': wLen.value})

        self.log(sys._getframe().f_code.co_name, error, ret, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)
        return ret

    # -------------------------------------------------------------------------
    # 2.4.8 PCO_SetCameraSetup
    # -------------------------------------------------------------------------
    def set_camera_setup(self, setup):
        """
        Command can be used to set the shutter mode of a pco.edge.This function
        is used to set the operation mode of the camera. If operation mode is
        changed, reboot_camera() must be called afterwards. It is recommended
        to set the command timeout to 2000 ms by calling set_timeouts() before
        changing the setup.

        :param setup: str

            * 'rolling shutter'
            * 'global shutter'
            * 'global reset'
        """

        self.SC2_Cam.PCO_SetCameraSetup.argtypes = [C.c_void_p,
                                                    C.c_uint16,
                                                    C.POINTER(C.c_uint32),
                                                    C.c_uint16]

        shutter_mode = {'rolling shutter': 0x00000001,
                        'global shutter': 0x00000002,
                        'global reset': 0x00000004}

        wType = C.c_uint16(0)
        dwSetup = (C.c_uint32 * 4)()
        dwSetup[0] = shutter_mode[setup]

        wLen = C.c_uint16(4)

        start_time = time.time()
        error = self.SC2_Cam.PCO_SetCameraSetup(self.camera_handle,
                                                wType,
                                                dwSetup,
                                                wLen)

        self.log(sys._getframe().f_code.co_name, error, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)

    # -------------------------------------------------------------------------
    # 2.4.9 PCO_ControlCommandCall
    # -------------------------------------------------------------------------
    def control_command_call(self, data):
        """
        This function issues a low level command to the camera. This call is
        part of most of the other calls. Normally calling this function is not
        needed. It can be used to cover those camera commands, which are not
        implemented in regular SDK functions.

        :param data: bytes
        """

        self.SC2_Cam.PCO_ControlCommandCall.argtypes = [C.c_void_p,
                                                        C.c_void_p,
                                                        C.c_uint,
                                                        C.c_void_p,
                                                        C.c_uint]

        size_in = (C.c_uint(len(data)))
        p_data_in = C.cast(data, C.POINTER(C.c_void_p))

        data_out = (C.c_uint8 * 300)()
        size_out = C.c_uint(300)
        p_data_out = C.cast(data_out, C.POINTER(C.c_void_p))

        start_time = time.time()
        error = self.SC2_Cam.PCO_ControlCommandCall(self.camera_handle,
                                                    p_data_in,
                                                    size_in,
                                                    p_data_out,
                                                    size_out)

        ret = {}
        if error == 0:
            length = int.from_bytes(bytes(data_out)[2:4], byteorder='little')
            ret.update({'response telegram': bytes(data_out)[0:length]})

        self.log(sys._getframe().f_code.co_name, error, ret, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)
        return ret

    # -------------------------------------------------------------------------
    # 2.4.10 PCO_GetFanControlParameters
    # -------------------------------------------------------------------------
    def get_fan_control_parameters(self):

        self.SC2_Cam.PCO_GetFanControlParameters.argtypes = [C.c_void_p,
                                                             C.POINTER(C.c_uint16),
                                                             C.POINTER(C.c_uint16),
                                                             C.POINTER(C.c_uint16),
                                                             C.c_uint16]
        wMode =  C.c_uint16()
        wValue =  C.c_uint16()
        wReserved =  C.c_uint16()
        wNumReserved =  C.c_uint16()

        start_time = time.time()
        error = self.SC2_Cam.PCO_GetFanControlParameters(self.camera_handle,
                                                         wMode,
                                                         wValue,
                                                         wReserved,
                                                         wNumReserved)

        mode_dict = {0: 'auto', 1: 'user'}
        ret = {}
        if error == 0:
            ret.update({'mode': mode_dict[wMode.value]})
            ret.update({'value': wValue.value})

        self.log(sys._getframe().f_code.co_name, error, ret, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)
        return ret

    # -------------------------------------------------------------------------
    # 2.4.11 PCO_SetFanControlParameters
    # -------------------------------------------------------------------------
    def set_fan_control_parameters(self, mode, value=100):

        self.SC2_Cam.PCO_SetFanControlParameters.argtypes = [C.c_void_p,
                                                             C.c_uint16,
                                                             C.c_uint16,
                                                             C.c_uint16,
                                                             C.c_uint16]

        if value not in range(0, 101, 1):
            raise ValueError

        if mode not in ['auto', 'user']:
            raise ValueError

        mode_dict = {'auto': 0x0000,
                     'user': 0x0001}

        wMode =  C.c_uint16(mode_dict[mode])
        wValue =  C.c_uint16(value)
        wReserved =  C.c_uint16()
        wNumReserved =  C.c_uint16()

        start_time = time.time()
        error = self.SC2_Cam.PCO_SetFanControlParameters(self.camera_handle,
                                                         wMode,
                                                         wValue,
                                                         wReserved,
                                                         wNumReserved)

        self.log(sys._getframe().f_code.co_name, error, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)


    # -------------------------------------------------------------------------
    # 2.5.1 PCO_GetSensorStruct (for the moment intentionally not implemented)
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # 2.5.2 PCO_SetSensorStruct (for the moment intentionally not implemented)
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # 2.5.3 PCO_GetSizes
    # -------------------------------------------------------------------------
    def get_sizes(self):
        """
        This function returns the current armed image size of the camera. If
        the user recently changed the size influencing values without
        issuing a arm_camera(), the get_sizes() function will return the
        sizes from the last recording. If no recording occurred, it will return
        the last ROI settings.

        :return: {'wXResAct': int,
                  'wYResAct': int,
                  'wXResMax': int,
                  'wYResMax': int}
        :rtype: dict
        """

        self.SC2_Cam.PCO_GetSizes.argtypes = [C.c_void_p,
                                              C.POINTER(C.c_uint16),
                                              C.POINTER(C.c_uint16),
                                              C.POINTER(C.c_uint16),
                                              C.POINTER(C.c_uint16)]

        wXResAct = C.c_uint16()
        wYResAct = C.c_uint16()
        wXResMax = C.c_uint16()
        wYResMax = C.c_uint16()

        start_time = time.time()
        error = self.SC2_Cam.PCO_GetSizes(self.camera_handle,
                                          wXResAct,
                                          wYResAct,
                                          wXResMax,
                                          wYResMax)

        ret = {}
        if error == 0:
            ret.update({'x': wXResAct.value})
            ret.update({'y': wYResAct.value})
            ret.update({'x max': wXResMax.value})
            ret.update({'y max': wYResMax.value})

        self.log(sys._getframe().f_code.co_name, error, ret, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)
        return ret

    # -------------------------------------------------------------------------
    # 2.5.4 PCO_GetSensorFormat
    # -------------------------------------------------------------------------
    def get_sensor_format(self):
        """
        This function retrieves the current sensor format. In the format
        [standard] only effective pixels are readout from the sensor. The
        readout in the format [extended] is camera dependent. Either a distinct
        region of the sensor is selected or the full sensor including
        effective, dark, reference and dummy pixels.

        :return: {'sensor format': int}
        :rtype: dict
        """

        self.SC2_Cam.PCO_GetSensorFormat.argtypes = [C.c_void_p,
                                                     C.POINTER(C.c_uint16)]

        wSensor = C.c_uint16()

        start_time = time.time()
        error = self.SC2_Cam.PCO_GetSensorFormat(self.camera_handle,
                                                 wSensor)

        ret = {}
        if error == 0:
            sensor_formats = {0: 'standard', 1: 'extended'}
            ret.update({'sensor format': sensor_formats[wSensor.value]})

        self.log(sys._getframe().f_code.co_name, error, ret, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)
        return ret

    # -------------------------------------------------------------------------
    # 2.5.5 PCO_SetSensorFormat
    # -------------------------------------------------------------------------
    def set_sensor_format(self, sensor_format):
        """
        This function sets the sensor format. In the format [standard] only
        effective pixels are readout from the sensor. The readout in the format
        [extended] is camera dependent. Either a distinct region of the sensor
        is selected or the full sensor including effective, dark, reference and
        dummy pixels.

        :param sensor_format: str

            * 'standard'
            * 'extended'

        >>> set_sensor_format()
        {'sensor format': 'standard'}

        >>> set_sensor_format()
        {'sensor format': 'extended'}

        """

        self.SC2_Cam.PCO_SetSensorFormat.argtypes = [C.c_void_p,
                                                     C.c_uint16]

        sensor_format_types = {'standard': 0x0000, 'extended': 0x0001}
        wSensor = C.c_uint16(sensor_format_types[sensor_format])

        start_time = time.time()
        error = self.SC2_Cam.PCO_SetSensorFormat(self.camera_handle,
                                                 wSensor)

        inp = {}
        inp.update({'sensor format': sensor_format})

        self.log(sys._getframe().f_code.co_name, error, inp, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)

    # -------------------------------------------------------------------------
    # 2.5.6 PCO_GetROI
    # -------------------------------------------------------------------------
    def get_roi(self):
        """
        :return: {'x0': int,
                  'y0': int,
                  'x1': int,
                  'y1': int}
        :rtype: dict

        >>> get_roi()
        {'x0': 1, 'y0': 1, 'x1': 512, 'y1': 512}

        """

        self.SC2_Cam.PCO_GetROI.argtypes = [C.c_void_p,
                                            C.POINTER(C.c_uint16),
                                            C.POINTER(C.c_uint16),
                                            C.POINTER(C.c_uint16),
                                            C.POINTER(C.c_uint16)]

        wRoiX0 = C.c_uint16()
        wRoiY0 = C.c_uint16()
        wRoiX1 = C.c_uint16()
        wRoiY1 = C.c_uint16()

        start_time = time.time()
        error = self.SC2_Cam.PCO_GetROI(self.camera_handle,
                                        wRoiX0,
                                        wRoiY0,
                                        wRoiX1,
                                        wRoiY1)

        ret = {}
        if error == 0:
            ret.update({'x0': wRoiX0.value,
                        'y0': wRoiY0.value,
                        'x1': wRoiX1.value,
                        'y1': wRoiY1.value})

        self.log(sys._getframe().f_code.co_name, error, ret, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)
        return ret

    # -------------------------------------------------------------------------
    # 2.5.7 PCO_SetROI
    # -------------------------------------------------------------------------
    def set_roi(self, x0, y0, x1, y1):
        """


        :param x0: int
        :param y0: int
        :param x1: int
        :param y1: int

        >>> set_roi(1, 1, 512, 512)

        """

        self.SC2_Cam.PCO_SetROI.argtypes = [C.c_void_p,
                                            C.c_uint16,
                                            C.c_uint16,
                                            C.c_uint16,
                                            C.c_uint16]

        wRoiX0 = C.c_uint16(x0)
        wRoiY0 = C.c_uint16(y0)
        wRoiX1 = C.c_uint16(x1)
        wRoiY1 = C.c_uint16(y1)

        start_time = time.time()
        error = self.SC2_Cam.PCO_SetROI(self.camera_handle,
                                        wRoiX0,
                                        wRoiY0,
                                        wRoiX1,
                                        wRoiY1)

        inp = {}
        inp.update({'x0': x0,
                    'y0': y0,
                    'x1': x1,
                    'y1': y1})

        self.log(sys._getframe().f_code.co_name, error, inp, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)

    # -------------------------------------------------------------------------
    # 2.5.8 PCO_GetBinning
    # -------------------------------------------------------------------------
    def get_binning(self):
        """
        Returns the binning values for x and y.

        :return: {'binning x': int
                'binning y': int}
        :rtype: dict

        >>> get_binning()
        {'binning x': 2, 'binning y': 2}

        """

        self.SC2_Cam.PCO_GetBinning.argtypes = [C.c_void_p,
                                                C.POINTER(C.c_uint16),
                                                C.POINTER(C.c_uint16)]

        wBinHorz = C.c_uint16()
        wBinVert = C.c_uint16()

        start_time = time.time()
        error = self.SC2_Cam.PCO_GetBinning(self.camera_handle,
                                            wBinHorz,
                                            wBinVert)

        ret = {}
        if error == 0:
            ret.update({'binning x': wBinHorz.value,
                        'binning y': wBinVert.value})

        self.log(sys._getframe().f_code.co_name, error, ret, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)
        return ret

    # -------------------------------------------------------------------------
    # 2.5.9 PCO_SetBinning
    # -------------------------------------------------------------------------
    def set_binning(self, x, y):
        """

        """

        self.SC2_Cam.PCO_SetBinning.argtypes = [C.c_void_p,
                                                C.c_uint16,
                                                C.c_uint16]

        #string_binning = {'1x1': (1, 1), '1x2': (1, 2), '1x4': (1, 4),
        #                  '2x1': (2, 1), '2x2': (2, 2), '2x4': (2, 4),
        #                  '4x1': (4, 1), '4x2': (4, 2), '4x4': (4, 4)}
        wBinHorz = C.c_uint16(x)
        wBinVert = C.c_uint16(y)

        start_time = time.time()
        error = self.SC2_Cam.PCO_SetBinning(self.camera_handle,
                                            wBinHorz, wBinVert)

        inp = {}
        inp.update({'binning x': x,
                    'binning y': y})
        self.log(sys._getframe().f_code.co_name, error, inp, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)

    # -------------------------------------------------------------------------
    # 2.5.10 PCO_GetPixelRate
    # -------------------------------------------------------------------------
    def get_pixel_rate(self):
        """
        Returns the currently active pixel rate.

        :return: {'pixel rate': int}
        :rtype: dict

        >>> get_pixel_ratee()
        {'pixel rate': 286000000}

        """

        self.SC2_Cam.PCO_GetPixelRate.argtypes = [C.c_void_p,
                                                  C.POINTER(C.c_uint32)]

        dwPixelRate = C.c_uint32()

        start_time = time.time()
        error = self.SC2_Cam.PCO_GetPixelRate(self.camera_handle,
                                              dwPixelRate)

        ret = {}
        if error == 0:
            ret.update({'pixel rate': dwPixelRate.value})

        self.log(sys._getframe().f_code.co_name, error, ret, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)
        return ret

    # -------------------------------------------------------------------------
    # 2.5.11 PCO_SetPixelRate
    # -------------------------------------------------------------------------
    def set_pixel_rate(self, pixel_rate):
        """
        Set the pixel rate.

        :param pixel_rate: int

        >>> set_pixel_rate(286_000_000)

        """

        self.SC2_Cam.PCO_SetPixelRate.argtypes = [C.c_void_p,
                                                  C.c_uint32]

        dwPixelRate = C.c_uint32(pixel_rate)

        start_time = time.time()
        error = self.SC2_Cam.PCO_SetPixelRate(self.camera_handle,
                                              dwPixelRate)

        inp = {}
        inp.update({'pixel rate': pixel_rate})

        self.log(sys._getframe().f_code.co_name, error, inp, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)

    # -------------------------------------------------------------------------
    # 2.5.12 PCO_GetConversionFactor
    # -------------------------------------------------------------------------
    def get_conversion_factor(self):
        """
        Get conversion factor (value x 10)

        :return: {'conversion factor': int}
        :rtype: dict

        >>> get_conversion_factor()
        {'conversion factor': 46}

        """

        self.SC2_Cam.PCO_GetConversionFactor.argtypes = [C.c_void_p,
                                                         C.POINTER(C.c_uint16)]

        wConvFact = C.c_uint16()

        start_time = time.time()
        error = self.SC2_Cam.PCO_GetConversionFactor(self.camera_handle,
                                                     wConvFact)

        ret = {}
        if error == 0:
            ret.update({'conversion factor': wConvFact.value})

        self.log(sys._getframe().f_code.co_name, error, ret, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)
        return ret

    # -------------------------------------------------------------------------
    # 2.5.13 PCO_SetConversionFactor
    # -------------------------------------------------------------------------
    def set_conversion_factor(self, conversion_factor):
        """
        Set conversion factor

        :param conversion_factor: int
        """

        self.SC2_Cam.PCO_SetConversionFactor.argtypes = [C.c_void_p,
                                                         C.c_uint16]

        wConvFact = C.c_uint16(conversion_factor)

        start_time = time.time()
        error = self.SC2_Cam.PCO_SetConversionFactor(self.camera_handle,
                                                     wConvFact)

        inp = {}
        inp.update({'conversion factor': conversion_factor})

        self.log(sys._getframe().f_code.co_name, error, inp, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)

    # -------------------------------------------------------------------------
    # 2.5.14 PCO_GetDoubleImageMode
    # -------------------------------------------------------------------------
    def get_double_image_mode(self):
        """
        Returns the double image mode.

        :return: {'double image': str}
        :rtype: dict

        >>> get_double_image_mode()
        {'double image': 'on'}

        >>> get_double_image_mode()
        {'double image': 'off'}

        """

        self.SC2_Cam.PCO_GetDoubleImageMode.argtypes = [C.c_void_p,
                                                        C.POINTER(C.c_uint16)]

        wDoubleImage = C.c_uint16()

        start_time = time.time()
        error = self.SC2_Cam.PCO_GetDoubleImageMode(self.camera_handle,
                                                    wDoubleImage)

        ret = {}
        if error == 0:
            double_image_mode = {0: 'off', 1: 'on'}
            ret.update({'double image': double_image_mode[wDoubleImage.value]})

        self.log(sys._getframe().f_code.co_name, error, ret, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)
        return ret

    # -------------------------------------------------------------------------
    # 2.5.15 PCO_SetDoubleImageMode
    # -------------------------------------------------------------------------
    def set_double_image_mode(self, mode):
        """
        Enables or disables the double image mode.

        >>> set_double_image_mode('on')

        >>> set_double_image_mode('off')

        """

        self.SC2_Cam.PCO_SetDoubleImageMode.argtypes = [C.c_void_p,
                                                        C.c_uint16]

        double_image_mode = {'off': 0, 'on': 1}

        start_time = time.time()
        error = self.SC2_Cam.PCO_SetDoubleImageMode(self.camera_handle,
                                                    double_image_mode[mode])

        inp = {}
        inp.update({'double image mode': mode})

        self.log(sys._getframe().f_code.co_name, error, inp, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)

    # -------------------------------------------------------------------------
    # 2.5.16 PCO_GetADCOperation
    # -------------------------------------------------------------------------
    def get_adc_operation(self):
        """
        """

        self.SC2_Cam.PCO_GetADCOperation.argtypes = [C.c_void_p,
                                                     C.POINTER(C.c_uint16)]

        wADCOperation = C.c_uint16()

        start_time = time.time()
        error = self.SC2_Cam.PCO_GetADCOperation(self.camera_handle,
                                                 wADCOperation)
        ret = {}
        if error == 0:
            adc_operation = {1: 'single adc', 2: 'dual adc', 16: 'panda'}
            ret.update({'adc operation': adc_operation[wADCOperation.value]})

        self.log(sys._getframe().f_code.co_name, error, ret, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)
        return ret

    # -------------------------------------------------------------------------
    # 2.5.17 PCO_SetADCOperation
    # -------------------------------------------------------------------------
    def set_adc_operation(self, mode):
        """

        >>> set_adc_operation('single adc')

        >>> set_adc_operation('dual adc')

        """

        self.SC2_Cam.PCO_SetADCOperation.argtypes = [C.c_void_p,
                                                     C.c_uint16]

        adc_operation = {'single adc': 1, 'dual adc': 2, 'panda': 16}
        wADCOperation = C.c_uint16(adc_operation[mode])

        start_time = time.time()
        error = self.SC2_Cam.PCO_SetADCOperation(self.camera_handle,
                                                 wADCOperation)

        inp = {}
        inp.update({'adc operation': mode})

        self.log(sys._getframe().f_code.co_name, error, inp, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)

    # -------------------------------------------------------------------------
    # 2.5.18 PCO_GetIRSensitivity
    # -------------------------------------------------------------------------
    def get_ir_sensitivity(self):
        """
        This function returns the IR sensitivity operating mode currently used
        from the camera.

        >>> get_ir_sensitivity()
        {'ir sensitivity': 'off'}

        >>> get_ir_sensitivity()
        {'ir sensitivity': 'on'}

        """

        self.SC2_Cam.PCO_GetIRSensitivity.argtypes = [C.c_void_p,
                                                      C.POINTER(C.c_uint16)]

        wIR = C.c_uint16()

        start_time = time.time()
        error = self.SC2_Cam.PCO_GetIRSensitivity(self.camera_handle,
                                                  wIR)

        ret = {}
        if error == 0:
            ir_sensitivity = {0: 'off', 1: 'on'}
            ret.update({'ir sensitivity': ir_sensitivity[wIR.value]})

        self.log(sys._getframe().f_code.co_name, error, ret, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)
        return ret

    # -------------------------------------------------------------------------
    # 2.5.19 PCO_SetIRSensitivity
    # -------------------------------------------------------------------------
    def set_ir_sensitivity(self, mode):
        """
        >>> set_ir_sensitivity('off')

        >>> set_ir_sensitivity('on')

        """

        self.SC2_Cam.PCO_SetIRSensitivity.argtypes = [C.c_void_p,
                                                      C.c_uint16]

        ir_sensitivity = {'off': 0, 'on': 1}
        wIR = C.c_uint16(ir_sensitivity[mode])

        start_time = time.time()
        error = self.SC2_Cam.PCO_SetIRSensitivity(self.camera_handle,
                                                  wIR)
        inp = {}
        inp.update({'ir sensitivity': mode})

        self.log(sys._getframe().f_code.co_name, error, inp, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)

    # -------------------------------------------------------------------------
    # 2.5.20 PCO_GetCoolingSetpointTemperature
    # -------------------------------------------------------------------------
    def get_cooling_setpoint_temperature(self):
        """

        >>> get_cooling_setpoint_temperature()
        {'cooling setpoint temperature': 7.0}

        """

        self.SC2_Cam.PCO_GetCoolingSetpointTemperature.argtypes = [C.c_void_p,
                                                                   C.POINTER(C.c_short)]

        sCoolSet = C.c_short()

        start_time = time.time()
        error = self.SC2_Cam.PCO_GetCoolingSetpointTemperature(self.camera_handle,
                                                               sCoolSet)

        ret = {}
        if error == 0:
            ret.update({'cooling setpoint temperature': float(sCoolSet.value)})

        self.log(sys._getframe().f_code.co_name, error, ret, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)
        return ret

    # -------------------------------------------------------------------------
    # 2.5.21 PCO_SetCoolingSetpointTemperature
    # -------------------------------------------------------------------------
    def set_cooling_setpoint_temperature(self, cooling_setpoint):
        """
        """

        self.SC2_Cam.PCO_SetCoolingSetpointTemperature.argtypes = [C.c_void_p,
                                                                   C.c_short]

        sCoolSet = C.c_short(int(cooling_setpoint))

        start_time = time.time()
        error = self.SC2_Cam.PCO_SetCoolingSetpointTemperature(self.camera_handle,
                                                               sCoolSet)

        inp = {}
        inp.update({'cooling setpoint temperature': cooling_setpoint})

        self.log(sys._getframe().f_code.co_name, error, inp, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)

    # -------------------------------------------------------------------------
    # 2.5.22 PCO_GetCoolingSetpoints
    # -------------------------------------------------------------------------
    ###########################################################################
    def get_cooling_setpoints(self):
        """
        """

        self.SC2_Cam.PCO_GetCoolingSetpoints.argtypes = [C.c_void_p,
                                                         C.c_uint16,
                                                         C.POINTER(C.c_uint16),
                                                         C.POINTER(C.c_short)]

        wNumSetPoints = C.c_uint16(100)
        sCoolSetpoints = (C.c_short * 100)()
        psCoolSetpoints = C.cast(sCoolSetpoints, C.POINTER(C.c_short))

        cooling_setpoints_list = []

        error = self.SC2_Cam.PCO_GetCoolingSetpoints(self.camera_handle,
                                                     0,
                                                     wNumSetPoints,
                                                     psCoolSetpoints)
        if error == 0:
            cooling_setpoints_list.append(float(sCoolSetpoints[0]))

        self.log(sys._getframe().f_code.co_name, error)

        for i in range(1, wNumSetPoints.value):

            error = self.SC2_Cam.PCO_GetCoolingSetpoints(self.camera_handle,
                                                         i,
                                                         wNumSetPoints,
                                                         psCoolSetpoints)
            if error == 0:
                cooling_setpoints_list.append(sCoolSetpoints[i])

        ret = {}
        ret.update({'cooling setpoints': cooling_setpoints_list})

        self.log(sys._getframe().f_code.co_name, error, ret)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)
        return ret

    # -------------------------------------------------------------------------
    # 2.5.23 PCO_GetOffsetMode
    # -------------------------------------------------------------------------
    def get_offset_mode(self):
        """


        :return: {'offset mode': str ['auto', 'off']}
        :rtype: dict

        >>> get_offset_mode()
        {'offset mode': 'auto'}

        >>> get_offset_mode()
        {'offset mode': 'off'}

        """

        self.SC2_Cam.PCO_GetOffsetMode.argtypes = [C.c_void_p,
                                                   C.POINTER(C.c_uint16)]

        wOffsetRegulation = C.c_uint16()

        start_time = time.time()
        error = self.SC2_Cam.PCO_GetOffsetMode(self.camera_handle,
                                               wOffsetRegulation)

        ret = {}
        if error == 0:
            offest_regulation = {0: 'auto', 1: 'off'}
            ret.update({'offset mode': offest_regulation[wOffsetRegulation.value]})

        self.log(sys._getframe().f_code.co_name, error, ret, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)
        return ret

    # -------------------------------------------------------------------------
    # 2.5.24 PCO_SetOffsetMode
    # -------------------------------------------------------------------------
    def set_offset_mode(self, mode):
        """


        :param mode: str

            * 'auto'
            * 'off'

        >>> set_offse_mode('auto')

        >>> set_offse_mode('off')

        """

        self.SC2_Cam.PCO_SetOffsetMode.argtypes = [C.c_void_p,
                                                   C.c_uint16]

        offset_regulation = {'auto': 0, 'off': 1}

        start_time = time.time()
        error = self.SC2_Cam.PCO_SetOffsetMode(self.camera_handle,
                                               offset_regulation[mode])

        inp = {}
        inp.update({'offset mode': mode})

        self.log(sys._getframe().f_code.co_name, error, inp, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)

    # -------------------------------------------------------------------------
    # 2.5.25 PCO_GetNoiseFilterMode
    # -------------------------------------------------------------------------
    def get_noise_filter_mode(self):
        """


        :return: {'noise filter mode': str}
        :rtype: dict
        """

        self.SC2_Cam.PCO_GetNoiseFilterMode.argtypes = [C.c_void_p,
                                                        C.POINTER(C.c_uint16)]

        wNoiseFilterMode = (C.c_uint16())

        start_time = time.time()
        error = self.SC2_Cam.PCO_GetNoiseFilterMode(self.camera_handle,
                                                    wNoiseFilterMode)

        ret = {}
        if error == 0:
            noise_filter_mode = {0: 'off',
                                 1: 'on',
                                 5: 'on & hot pixel correction'}
            ret.update({'noise filter mode': noise_filter_mode[wNoiseFilterMode.value]})

        self.log(sys._getframe().f_code.co_name, error, ret, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)
        return ret

    # -------------------------------------------------------------------------
    # 2.5.26 PCO_SetNoiseFilterMode
    # -------------------------------------------------------------------------
    def set_noise_filter_mode(self, mode):
        """


        :param mode: str

            * 'off'
            * 'on'
            * 'on & hot pixel correction'
        """

        self.SC2_Cam.PCO_SetNoiseFilterMode.argtypes = [C.c_void_p,
                                                        C.c_uint16]

        noise_filter_mode = {'off': 0,
                             'on': 1,
                             'on & hot pixel correction': 5}

        start_time = time.time()
        error = self.SC2_Cam.PCO_SetNoiseFilterMode(self.camera_handle,
                                                    noise_filter_mode[mode])

        inp = {'noise filter mode': mode}

        self.log(sys._getframe().f_code.co_name, error, inp, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)

    # -------------------------------------------------------------------------
    # 2.5.27 PCO_GetLookuptableInfo (for the moment intentionally not implemented)
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # 2.5.28 PCO_GetActiveLookuptable (for the moment intentionally not implemented)
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # 2.5.29 PCO_SetActiveLookuptable (for the moment intentionally not implemented)
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # 2.6.1 PCO_GetTimingStruct (for the moment intentionally not implemented)
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # 2.6.2 PCO_SetTimingStruct (for the moment intentionally not implemented)
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # 2.6.3 PCO_GetCOCRunTime
    # -------------------------------------------------------------------------
    def get_coc_runtime(self):
        """


        :return: {'time second': int
                'time nanosecond': int}
        :rtype: dict
        """

        self.SC2_Cam.PCO_GetCOCRuntime.argtypes = [C.c_void_p,
                                                   C.POINTER(C.c_uint32),
                                                   C.POINTER(C.c_uint32)]

        dwTime_s = C.c_uint32()
        dwTime_ns = C.c_uint32()

        start_time = time.time()
        error = self.SC2_Cam.PCO_GetCOCRuntime(self.camera_handle,
                                               dwTime_s,
                                               dwTime_ns)

        ret = {}
        if error == 0:
            ret.update({'time second': float(dwTime_s.value)})
            ret.update({'time nanosecond': float(dwTime_ns.value)})
            ret.update({'coc runtime': dwTime_s.value + dwTime_ns.value * 1e-9})


        self.log(sys._getframe().f_code.co_name, error, ret, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)
        return ret

    # -------------------------------------------------------------------------
    # 2.6.4 PCO_GetDelayExposureTime
    # -------------------------------------------------------------------------
    def get_delay_exposure_time(self):
        """


        :return: {'delay': int,
                'delay timebase': str,
                'exposure': int,
                'exposure timebase': str}
        :rtype: dict


        >>> get_delay_exposure_timeime()
        {'delay': 0, 'exposure': 10,
         'delay timebase': 'ms', 'exposure timebase': 'ms'}

        """

        self.SC2_Cam.PCO_GetDelayExposureTime.argtypes = [C.c_void_p,
                                                          C.POINTER(C.c_uint32),
                                                          C.POINTER(C.c_uint32),
                                                          C.POINTER(C.c_uint16),
                                                          C.POINTER(C.c_uint16)]

        dwDelay = C.c_uint32()
        dwExposure = C.c_uint32()
        wTimeBaseDelay = C.c_uint16()
        wTimeBaseExposure = C.c_uint16()

        start_time = time.time()
        error = self.SC2_Cam.PCO_GetDelayExposureTime(self.camera_handle,
                                                      dwDelay,
                                                      dwExposure,
                                                      wTimeBaseDelay,
                                                      wTimeBaseExposure)

        ret = {}
        if error == 0:
            timebase = {0: 'ns', 1: 'us', 2: 'ms'}
            ret.update({'delay': dwDelay.value})
            ret.update({'exposure': dwExposure.value})
            ret.update({'delay timebase': timebase[wTimeBaseDelay.value]})
            ret.update({'exposure timebase': timebase[wTimeBaseExposure.value]})

        self.log(sys._getframe().f_code.co_name, error, ret, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)
        return ret

    # -------------------------------------------------------------------------
    # 2.6.5 PCO_SetDelayExposureTime
    # -------------------------------------------------------------------------
    def set_delay_exposure_time(self, delay, delay_timebase, exposure, exposure_timebase):
        """


        :param delay: int
        :param delay_timebase: str ['ms', 'us', 'ns']
        :param exposure: int
        :param exposure_timebase: str ['ms', 'us', 'ns']

        >>> set_delay_exposure_time(0, 'ms', 10, 'ms')

        """

        self.SC2_Cam.PCO_SetDelayExposureTime.argtypes = [C.c_void_p,
                                                          C.c_uint32,
                                                          C.c_uint32,
                                                          C.c_uint16,
                                                          C.c_uint16]

        timebase = {'ns': 0, 'us': 1, 'ms': 2}

        start_time = time.time()
        error = self.SC2_Cam.PCO_SetDelayExposureTime(self.camera_handle,
                                                    delay,
                                                    exposure,
                                                    timebase[delay_timebase],
                                                    timebase[exposure_timebase])

        inp = {}
        inp.update({'delay': delay,
                    'delay timebase': delay_timebase,
                    'exposure': exposure,
                    'exposure timebase': exposure_timebase})

        self.log(sys._getframe().f_code.co_name, error, inp, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)

    # -------------------------------------------------------------------------
    # 2.6.6 PCO_GetDelayExposureTimeTable (for the moment intentionally not implemented)
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # 2.6.7 PCO_SetDelayExposureTimeTable (for the moment intentionally not implemented)
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # 2.6.8 PCO_GetFrameRate
    # -------------------------------------------------------------------------
    def get_frame_rate(self):
        """


        :return: {'status': int,
                  'frame rate mHz': int,
                  'exposure time ns': int,}
        :rtype: dict
        """

        self.SC2_Cam.PCO_GetFrameRate.argtypes = [C.c_void_p,
                                                  C.POINTER(C.c_uint16),
                                                  C.POINTER(C.c_uint32),
                                                  C.POINTER(C.c_uint32)]

        wFrameRateStatus = C.c_uint16()
        dwFrameRate = C.c_uint32()
        dwFrameRateExposure = C.c_uint32()

        start_time = time.time()
        error = self.SC2_Cam.PCO_GetFrameRate(self.camera_handle,
                                              wFrameRateStatus,
                                              dwFrameRate,
                                              dwFrameRateExposure)

        ret = {}
        if error == 0:
            ret.update({'status': wFrameRateStatus.value,
                        'frame rate mHz': dwFrameRate.value,
                        'exposure time ns': dwFrameRateExposure.value})

        self.log(sys._getframe().f_code.co_name, error, ret, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)
        return ret

    # -------------------------------------------------------------------------
    # 2.6.9 PCO_SetFrameRate
    # -------------------------------------------------------------------------
    def set_frame_rate(self, frame_rate_mhz, exposure_time_ns):
        """

        """

        self.SC2_Cam.PCO_SetFrameRate.argtypes = [C.c_void_p,
                                                  C.POINTER(C.c_uint16),
                                                  C.c_uint16,
                                                  C.POINTER(C.c_uint32),
                                                  C.POINTER(C.c_uint32)]

        wFrameRateStatus = C.c_uint16()
        wFrameRateMode = C.c_uint16()
        dwFrameRate = C.c_uint32(frame_rate_mhz)
        dwFrameRateExposure = C.c_uint32(exposure_time_ns)

        start_time = time.time()
        error = self.SC2_Cam.PCO_SetFrameRate(self.camera_handle,
                                              wFrameRateStatus,
                                              wFrameRateMode,
                                              dwFrameRate,
                                              dwFrameRateExposure)

        ret = {}
        if error == 0:
            ret.update({'status': wFrameRateStatus.value,
                        'mode': wFrameRateMode.value,
                        'frame rate mHz': dwFrameRate.value,
                        'exposure time ns': dwFrameRateExposure.value})

        self.log(sys._getframe().f_code.co_name, error, ret, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)
        return ret

    # -------------------------------------------------------------------------
    # 2.6.10 PCO_GetFPSExposureMode
    # -------------------------------------------------------------------------
    def get_fps_exposure_mode(self):
        """
        This function returns the status of FPS exposure mode setting and
        according exposure time information.
        """

        self.SC2_Cam.PCO_GetFPSExposureMode.argtypes = [C.c_void_p,
                                                        C.POINTER(C.c_uint16),
                                                        C.POINTER(C.c_uint32)]

        wFPSExposureMode = C.c_uint16()
        dwFPSExposureTime = C.c_uint32()

        start_time = time.time()
        error = self.SC2_Cam.PCO_GetFPSExposureMode(self.camera_handle,
                                                    wFPSExposureMode,
                                                    dwFPSExposureTime)

        ret = {}
        if error == 0:
            fps_exposure_mode = {0: 'off', 1: 'on'}
            ret.update({'fps exposure mode': fps_exposure_mode[wFPSExposureMode.value],
                        'fps exposure time': fps_exposure_mode[dwFPSExposureTime.value]})

        self.log(sys._getframe().f_code.co_name, error, ret, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)
        return ret

    # -------------------------------------------------------------------------
    # 2.6.11 PCO_SetFPSExposureMode
    # -------------------------------------------------------------------------
    def set_fps_exposure_mode(self, fps_exposure_mode):
        """
        This function does set the image timing of the camera so that the
        maximum frame rate and the maximum exposure time for this frame rate is
        achieved. The maximum image frame rate (FPS = frames per second)
        depends on the pixel rate and the image area selection.
        """
        self.SC2_Cam.PCO_SetFPSExposureMode.argtypes = [C.c_void_p,
                                                        C.c_uint16,
                                                        C.POINTER(C.c_uint32)]

        mode = {'off': 0, 'on': 1}
        wFPSExposureMode = C.c_uint16(mode[fps_exposure_mode])
        dwFPSExposureTime = C.c_uint32()

        start_time = time.time()
        error = self.SC2_Cam.PCO_SetFPSExposureMode(self.camera_handle,
                                                    wFPSExposureMode,
                                                    dwFPSExposureTime)

        ret = {}
        if error == 0:
            ret.update({'fps exposure time [ns]': dwFPSExposureTime.value})

        self.log(sys._getframe().f_code.co_name, error, ret, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)
        return ret

    # -------------------------------------------------------------------------
    # 2.6.12 PCO_GetTriggerMode
    # -------------------------------------------------------------------------
    def get_trigger_mode(self):
        """

        :return: {'trigger mode': str}
        :rtype: dict
        """

        self.SC2_Cam.PCO_GetTriggerMode.argtypes = [C.c_void_p,
                                                    C.POINTER(C.c_uint16)]

        wTriggerMode = C.c_uint16()

        start_time = time.time()
        error = self.SC2_Cam.PCO_GetTriggerMode(self.camera_handle,
                                                wTriggerMode)

        ret = {}
        if error == 0:
            trigger_mode = {0: 'auto sequence',
                            1: 'software trigger',
                            2: 'external exposure start & software trigger',
                            3: 'external exposure control',
                            4: 'external synchronized',
                            5: 'fast external exposure control',
                            6: 'external CDS control',
                            7: 'slow external exposure control',
                            258: 'external synchronized HDSDI'}
            ret.update({'trigger mode': trigger_mode[wTriggerMode.value]})

        self.log(sys._getframe().f_code.co_name, error, ret, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)
        return ret

    # -------------------------------------------------------------------------
    # 2.6.13 PCO_SetTriggerMode
    # -------------------------------------------------------------------------
    def set_trigger_mode(self, mode):
        """


        :param mode: str

            * 'auto sequence'
            * 'software trigger'
            * 'external exposure start & software trigger'
            * 'external exposure control'
            * 'external synchronized'
            * 'fast external exposure control'
            * 'external CDS control'
            * 'slow external exposure control'
            * 'external synchronized HDSDI'
        """

        self.SC2_Cam.PCO_SetTriggerMode.argtypes = [C.c_void_p,
                                                    C.c_uint16]

        trigger_mode = {'auto sequence': 0,
                        'software trigger': 1,
                        'external exposure start & software trigger': 2,
                        'external exposure control': 3,
                        'external synchronized': 4,
                        'fast external exposure control': 5,
                        'external CDS control': 6,
                        'slow external exposure control': 7,
                        'external synchronized HDSDI': 258}

        start_time = time.time()
        error = self.SC2_Cam.PCO_SetTriggerMode(self.camera_handle,
                                                trigger_mode[mode])

        inp = {}
        inp.update({'trigger mode': mode})

        self.log(sys._getframe().f_code.co_name, error, inp, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)

    # -------------------------------------------------------------------------
    # 2.6.14 PCO_ForceTrigger
    # -------------------------------------------------------------------------
    def force_trigger(self):
        """
        Force software trigger

        >>> force_trigger()
        {'triggered': unsuccessful}

        >>> force_trigger()
        {'triggered': successful}

        """

        self.SC2_Cam.PCO_ForceTrigger.argtypes = [C.c_void_p,
                                                  C.POINTER(C.c_uint16)]

        wTriggered = C.c_uint16()

        start_time = time.time()
        error = self.SC2_Cam.PCO_ForceTrigger(self.camera_handle,
                                              wTriggered)

        ret = {}
        if error == 0:
            state = {0: 'unsuccessful', 1: 'successful'}
            ret.update({'triggered': state[wTriggered.value]})

        self.log(sys._getframe().f_code.co_name, error, ret, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)
        return ret

    # -------------------------------------------------------------------------
    # 2.6.15 PCO_GetCameraBusyStatus
    # -------------------------------------------------------------------------
    def get_camera_busy_status(self):
        """


        :return: {'busy status': int}
        :rtype: dict

        >>> get_camera_busy_status()
        {'busy status': ready}

        >>> get_camera_busy_status()
        {'busy status': busy}

        """

        self.SC2_Cam.PCO_GetCameraBusyStatus.argtypes = [C.c_void_p,
                                                         C.POINTER(C.c_uint16)]

        wCameraBusyState = C.c_uint16()

        start_time = time.time()
        error = self.SC2_Cam.PCO_GetCameraBusyStatus(self.camera_handle,
                                                     wCameraBusyState)

        ret = {}
        if error == 0:
            busy_status = {0: 'ready', 1: 'busy'}
            ret.update({'busy status': busy_status[wCameraBusyState.value]})

        self.log(sys._getframe().f_code.co_name, error, ret, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)
        return ret

    # -------------------------------------------------------------------------
    # 2.6.16 PCO_GetPowerDownMode (for the moment intentionally not implemented)
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # 2.6.17 PCO_SetPowerDownMode (for the moment intentionally not implemented)
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # 2.6.18 PCO_GetUserPowerDownTime (for the moment intentionally not implemented)
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # 2.6.19 PCO_SetUserPowerDownTime (for the moment intentionally not implemented)
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # 2.6.20 PCO_GetModulationMode (for the moment intentionally not implemented)
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # 2.6.21 PCO_SetModulationMode (for the moment intentionally not implemented)
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # 2.6.22 PCO_GetHWIOSignalCount
    # -------------------------------------------------------------------------
    def get_hwio_signal_count(self):
        """
        This function returns the number of hardware I/O signal lines, which
        are available at the camera.
        """

        self.SC2_Cam.PCO_GetHWIOSignalCount.argtypes = [C.c_void_p,
                                                        C.POINTER(C.c_uint16)]

        wNumSignals = C.c_uint16()

        start_time = time.time()
        error = self.SC2_Cam.PCO_GetHWIOSignalCount(self.camera_handle,
                                                    wNumSignals)

        ret = {}
        if error == 0:
            ret.update({'hwio signal count': wNumSignals.value})

        self.log(sys._getframe().f_code.co_name, error, ret, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)
        return ret

    # -------------------------------------------------------------------------
    # 2.6.23 PCO_GetHWIOSignalDescriptor
    # -------------------------------------------------------------------------
    def get_hwio_signal_descriptor(self, signal_number):
        """
        This function does retrieve the description of a distinct hardware
        I/O signal line.
        """

        class PCO_SINGLE_SIGNAL_DESC(C.Structure):
            _pack_ = 1
            _fields_ = [
                ("wSize", C.c_uint16),
                ("ZZwAlignDummy1", C.c_uint16),
                ("strSignalName", C.c_uint8 * 100),
                ("wSignalDefinitions", C.c_uint16),
                ("wSignalTypes", C.c_uint16),
                ("wSignalPolarity", C.c_uint16),
                ("wSignalFilter", C.c_uint16),
                ("dwDummy", C.c_uint32 * 22)]

        self.SC2_Cam.PCO_GetHWIOSignalDescriptor.argtypes = [C.c_void_p,
                                                             C.c_uint16,
                                                             C.POINTER(PCO_SINGLE_SIGNAL_DESC)]

        wSignalNum = C.c_uint16(signal_number)
        pstrSignal = PCO_SINGLE_SIGNAL_DESC()
        pstrSignal.wSize = C.sizeof(PCO_SINGLE_SIGNAL_DESC)

        start_time = time.time()
        error = self.SC2_Cam.PCO_GetHWIOSignalDescriptor(self.camera_handle,
                                                         wSignalNum,
                                                         pstrSignal)

        ret = {}
        if error == 0:

            temp_list = []
            for n in range(4):
                for i in range(0+n*25, 25+n*25):
                    temp_list.append(pstrSignal.strSignalName[i])

            signal_names = [bytes(temp_list[0:25]).decode('ascii').strip("\0"),
                            bytes(temp_list[25:50]).decode('ascii').strip("\0"),
                            bytes(temp_list[50:75]).decode('ascii').strip("\0"),
                            bytes(temp_list[75:100]).decode('ascii').strip("\0")]

            ret.update({'signal name': signal_names,
                        'signal definition': pstrSignal.wSignalDefinitions,
                        'signal types': pstrSignal.wSignalTypes,
                        'signal polarity': pstrSignal.wSignalPolarity,
                        'signal filter': pstrSignal.wSignalFilter})

        self.log(sys._getframe().f_code.co_name, error, ret, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)
        return ret

    # -------------------------------------------------------------------------
    # 2.6.24 PCO_GetHWIOSignal
    # -------------------------------------------------------------------------
    def get_hwio_signal(self, index):
        """
        This function returns the current settings of a distinct hardware input/output (IO) signal line.
        """

        class PCO_SIGNAL_STRUCT(C.Structure):
            _pack_ = 1
            _fields_ = [
                ("wSize", C.c_uint16),
                ("wSignalNum", C.c_uint16),
                ("wEnabled", C.c_uint16),
                ("wType", C.c_uint16),
                ("wPolarity", C.c_uint16),
                ("wFilter", C.c_uint16),
                ("wSelected", C.c_uint16),
                ("ZzwReserved", C.c_uint16),
                ("dwParameter", C.c_uint32 * 4),
                ("dwSignalFunctionality", C.c_uint32 * 4),
                ("ZzdwReserved", C.c_uint32 * 3)]

        self.SC2_Cam.PCO_GetHWIOSignal.argtypes = [C.c_void_p,
                                                   C.c_uint16,
                                                   C.POINTER(PCO_SIGNAL_STRUCT)]

        wSignalNum = C.c_uint16(index)

        strHWIOSignal = PCO_SIGNAL_STRUCT()
        strHWIOSignal.wSize = C.sizeof(PCO_SIGNAL_STRUCT)

        start_time = time.time()
        error = self.SC2_Cam.PCO_GetHWIOSignal(self.camera_handle,
                                               wSignalNum,
                                               strHWIOSignal)

        ret = {}
        if error == 0:
            wEnabled_states = {0x0000: 'off',
                               0x0001: 'on'}

            wType_states = {0x0001: 'TTL',
                            0x0002: 'high level TTL',
                            0x0004: 'contact mode',
                            0x0008: 'RS485 differential',
                            0x0080: 'two pin differential'}

            wPolarity_states = {0x0001: 'high level',
                                0x0002: 'low level',
                                0x0004: 'rising edge',
                                0x0008: 'falling edge'}

            wFilter_state = {0x0000: 'error',
                             0x0001: 'off',
                             0x0002: 'medium',
                             0x0004: 'high'}

            parameter = [strHWIOSignal.dwParameter[0],
                         strHWIOSignal.dwParameter[1],
                         strHWIOSignal.dwParameter[2],
                         strHWIOSignal.dwParameter[3]]

            functionality = [strHWIOSignal.dwSignalFunctionality[0],
                             strHWIOSignal.dwSignalFunctionality[1],
                             strHWIOSignal.dwSignalFunctionality[2],
                             strHWIOSignal.dwSignalFunctionality[3]]


            ret.update({'enabled': wEnabled_states[strHWIOSignal.wEnabled]})
            ret.update({'type': wType_states[strHWIOSignal.wType]})
            ret.update({'polarity': wPolarity_states[strHWIOSignal.wPolarity]})
            ret.update({'filter': wFilter_state[strHWIOSignal.wFilter]})
            ret.update({'selected': strHWIOSignal.wSelected})
            ret.update({'parameter': parameter})
            ret.update({'signal functionality': functionality})

        self.log(sys._getframe().f_code.co_name, error, ret, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)
        return ret

    # -------------------------------------------------------------------------
    # 2.6.25 PCO_SetHWIOSignal
    # -------------------------------------------------------------------------
    def set_hwio_signal(self, index, enabled, signal_type, polarity, filter_type, selected, parameter):
        """
        This function does select the settings of a distinct hardware IO signal line.
        """

        class PCO_SIGNAL_STRUCT(C.Structure):
            _pack_ = 1
            _fields_ = [
                ("wSize", C.c_uint16),
                ("wSignalNum", C.c_uint16),
                ("wEnabled", C.c_uint16),
                ("wType", C.c_uint16),
                ("wPolarity", C.c_uint16),
                ("wFilter", C.c_uint16),
                ("wSelected", C.c_uint16),
                ("ZzwReserved", C.c_uint16),
                ("dwParameter", C.c_uint32 * 4),
                ("dwSignalFunctionality", C.c_uint32 * 4),
                ("ZzdwReserved", C.c_uint32 * 3)]

        self.SC2_Cam.PCO_SetHWIOSignal.argtypes = [C.c_void_p,
                                                   C.c_uint16,
                                                   C.POINTER(PCO_SIGNAL_STRUCT)]

        wEnabled_states = {'off': 0x0000,
                           'on': 0x0001}

        wType_states = {'TTL': 0x0001,
                        'high level TTL': 0x0002,
                        'contact mode': 0x0004,
                        'RS485 differential': 0x0008,
                        'two pin differential': 0x0080}

        wPolarity_states = {'high level': 0x0001,
                            'low level': 0x0002,
                            'rising edge': 0x0004,
                            'falling edge': 0x0008}

        wFilter_state = {'off': 0x0001,
                         'medium': 0x0002,
                         'high': 0x0004}

        wSignalNum = C.c_uint16(index)
        strHWIOSignal = PCO_SIGNAL_STRUCT()
        strHWIOSignal.wSize = C.sizeof(PCO_SIGNAL_STRUCT)

        strHWIOSignal.wEnabled = wEnabled_states[enabled]
        strHWIOSignal.wType = wType_states[signal_type]
        strHWIOSignal.wPolarity = wPolarity_states[polarity]
        strHWIOSignal.wFilter = wFilter_state[filter_type]
        
        strHWIOSignal.wSelected = selected
        
        strHWIOSignal.dwParameter[0] = parameter[0]
        strHWIOSignal.dwParameter[1] = parameter[1]
        strHWIOSignal.dwParameter[2] = parameter[2]
        strHWIOSignal.dwParameter[3] = parameter[3]

        start_time = time.time()
        error = self.SC2_Cam.PCO_SetHWIOSignal(self.camera_handle,
                                               wSignalNum,
                                               strHWIOSignal)

        inp = {}
        inp.update({'index': index,
                    'enabled': enabled,
                    'signal type': signal_type,
                    'polarity': polarity,
                    'filter type': filter_type})

        self.log(sys._getframe().f_code.co_name, error, inp, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)

    # -------------------------------------------------------------------------
    # 2.6.26 PCO_GetImageTiming
    # -------------------------------------------------------------------------
    def get_image_timing(self):
        """
        This function returns the current image timing in nanosecond resolution
        and additional trigger system information.
        """

        class PCO_IMAGE_TIMING(C.Structure):
            _pack_ = 1
            _fields_ = [
                ("wSize", C.c_uint16),
                ("wDummy", C.c_uint16),
                ("FrameTime_ns", C.c_uint32),
                ("FrameTime_s", C.c_uint32),
                ("ExposureTime_ns", C.c_uint32),
                ("ExposureTime_s", C.c_uint32),
                ("TriggerSystemDelay_ns", C.c_uint32),
                ("TriggerSystemJitter_ns", C.c_uint32),
                ("TriggerDelay_ns", C.c_uint32),
                ("TriggerDelay_s", C.c_uint32),
                ("ZZdwDummy", C.c_uint32 * 11)]

        self.SC2_Cam.PCO_GetImageTiming.argtypes = [C.c_void_p,
                                                    C.POINTER(PCO_IMAGE_TIMING)]

        pstrImageTiming = PCO_IMAGE_TIMING()
        pstrImageTiming.wSize = C.sizeof(PCO_IMAGE_TIMING)

        start_time = time.time()
        error = self.SC2_Cam.PCO_GetImageTiming(self.camera_handle,
                                                pstrImageTiming)

        ret = {}
        if error == 0:
            ret.update({'frame time ns': pstrImageTiming.FrameTime_ns})
            ret.update({'frame time s': pstrImageTiming.FrameTime_s})
            ret.update({'exposure time ns': pstrImageTiming.ExposureTime_ns})
            ret.update({'exposure time s': pstrImageTiming.ExposureTime_s})
            ret.update({'trigger system delay ns': pstrImageTiming.TriggerSystemDelay_ns})
            ret.update({'trigger system jitter ns': pstrImageTiming.TriggerSystemJitter_ns})
            ret.update({'trigger delay ns': pstrImageTiming.TriggerDelay_ns})
            ret.update({'trigger delay s': pstrImageTiming.TriggerDelay_s})

        self.log(sys._getframe().f_code.co_name, error, ret, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)
        return ret

    # -------------------------------------------------------------------------
    # 2.6.27 PCO_GetCameraSynchMode
    # -------------------------------------------------------------------------
    def get_camera_synch_mode(self):
        """
        """

        self.SC2_Cam.PCO_GetCameraSynchMode.argtypes = [C.c_void_p,
                                                        C.POINTER(C.c_uint16)]

        wCameraSynchMode = C.c_uint16()

        start_time = time.time()
        error = self.SC2_Cam.PCO_GetCameraSynchMode(self.camera_handle,
                                                    wCameraSynchMode)

        ret = {}
        if error == 0:
            mode = {0: 'off', 1: 'master', 2: 'slave'}
            ret.update({'camera sync mode': mode[wCameraSynchMode.value]})

        self.log(sys._getframe().f_code.co_name, error, ret, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)
        return ret

    # -------------------------------------------------------------------------
    # 2.6.28 PCO_SetCameraSynchMode
    # -------------------------------------------------------------------------
    def set_camera_synch_mode(self, synch_mode):
        """
        """

        self.SC2_Cam.PCO_SetCameraSynchMode.argtypes = [C.c_void_p,
                                                        C.c_uint16]

        mode = {'off': 0, 'master': 1, 'slave': 2}
        wCameraSynchMode = C.c_uint16(mode[synch_mode])

        start_time = time.time()
        error = self.SC2_Cam.PCO_SetCameraSynchMode(self.camera_handle,
                                                    wCameraSynchMode)

        inp = {}
        inp.update({'synch mode': synch_mode})

        self.log(sys._getframe().f_code.co_name, error, inp, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)

    # -------------------------------------------------------------------------
    # 2.6.29 PCO_GetExpTrigSignalStatus
    # -------------------------------------------------------------------------
    def get_exposure_trigger_signal_status(self):
        """
        Get exposure trigger signal status

        :return: {'exposure trigger signal status': str}
        :rtype: dict
        """

        self.SC2_Cam.PCO_GetExpTrigSignalStatus.argtypes = [C.c_void_p,
                                                            C.POINTER(C.c_uint16)]

        wExposureTriggerSignalStatus = C.c_uint16()

        start_time = time.time()
        error = self.SC2_Cam.PCO_GetExpTrigSignalStatus(self.camera_handle,
                                                        wExposureTriggerSignalStatus)

        ret = {}
        if error == 0:
            status = {0: 'off', 1: 'on'}
            ret.update({'exposure trigger signal status': status[wExposureTriggerSignalStatus.value]})

        self.log(sys._getframe().f_code.co_name, error, ret, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)
        return ret

    # -------------------------------------------------------------------------
    # 2.6.30 PCO_GetFastTimingMode
    # -------------------------------------------------------------------------
    def get_fast_timing_mode(self):
        """
        """

        self.SC2_Cam.PCO_GetFastTimingMode.argtypes = [C.c_void_p,
                                                       C.POINTER(C.c_uint16)]

        wFastTimingMode = C.c_uint16()

        start_time = time.time()
        error = self.SC2_Cam.PCO_GetFastTimingMode(self.camera_handle,
                                                   wFastTimingMode)

        ret = {}
        if error == 0:
            mode = {0: 'off', 1: 'on'}
            ret.update({'fast timing mode': mode[wFastTimingMode.value]})

        self.log(sys._getframe().f_code.co_name, error, ret, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)
        return ret

    # -------------------------------------------------------------------------
    # 2.6.31 PCO_SetFastTimingMode
    # -------------------------------------------------------------------------
    def set_fast_timing_mode(self, fast_timing_mode):
        """
        """

        self.SC2_Cam.PCO_SetFastTimingMode.argtypes = [C.c_void_p,
                                                       C.c_uint16]

        mode = {'off': 0, 'on': 1}
        wFastTimingMode = C.c_uint16(mode[fast_timing_mode])

        start_time = time.time()
        error = self.SC2_Cam.PCO_SetFastTimingMode(self.camera_handle,
                                                   wFastTimingMode)

        inp = {}
        inp.update({'fast timing mode': fast_timing_mode})

        self.log(sys._getframe().f_code.co_name, error, inp, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)

    # -------------------------------------------------------------------------
    # 2.7.1 PCO_GetRecordingStruct
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # 2.7.2 PCO_SetRecordingStruct
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # 2.7.3 PCO_GetRecordingState
    # -------------------------------------------------------------------------
    def get_recording_state(self):
        """
        Returns the current recording state of the camera.

        :return: {'recording state': str}
        :rtype: dict

        >>> get_recording_state()
        {'recording state': 'off'}

        >>> get_recording_state()
        {'recording state': 'on'}

        """

        self.SC2_Cam.PCO_GetRecordingState.argtypes = [C.c_void_p,
                                                       C.POINTER(C.c_uint16)]

        wRecState = C.c_uint16()

        start_time = time.time()
        error = self.SC2_Cam.PCO_GetRecordingState(self.camera_handle,
                                                   wRecState)

        ret = {}
        if error == 0:
            recording_state = {0: 'off', 1: 'on'}
            ret.update({'recording state': recording_state[wRecState.value]})

        self.log(sys._getframe().f_code.co_name, error, ret, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)
        return ret

    # -------------------------------------------------------------------------
    # 2.7.4 PCO_SetRecordingState
    # -------------------------------------------------------------------------
    def set_recording_state(self, state):
        """
        Set recording state

        :param state: str

            * 'on'
            * 'off'


        """

        self.SC2_Cam.PCO_SetRecordingState.argtypes = [C.c_void_p,
                                                       C.c_uint16]

        recording_state = {'off': 0, 'on': 1}

        start_time = time.time()
        error = self.SC2_Cam.PCO_SetRecordingState(self.camera_handle,
                                                recording_state[state])

        inp = {}
        inp.update({'recording state': state})

        self.log(sys._getframe().f_code.co_name, error, inp, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)

    # -------------------------------------------------------------------------
    # 2.7.5 PCO_GetStorageMode
    # -------------------------------------------------------------------------
    def get_storage_mode(self):
        """
        This function returns the current storage mode of the camera. Storage
        mode is either [recorder] or [FIFO buffer].
        """

        self.SC2_Cam.PCO_GetStorageMode.argtypes = [C.c_void_p,
                                                    C.POINTER(C.c_uint16)]

        wStorageMode = C.c_uint16()

        start_time = time.time()
        error = self.SC2_Cam.PCO_GetStorageMode(self.camera_handle,
                                                wStorageMode)

        ret = {}
        if error == 0:
            storage_mode = {0: 'recorder', 1: 'fifo'}
            ret.update({'storage mode': storage_mode[wStorageMode.value]})

        self.log(sys._getframe().f_code.co_name, error, ret, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)
        return ret

    # -------------------------------------------------------------------------
    # 2.7.6 PCO_SetStorageMode
    # -------------------------------------------------------------------------
    def set_storage_mode(self, mode):
        """
        This function does set the storage mode of the camera. Storage mode can
        be set to either [recorder] or [FIFO buffer] mode.
        """

        self.SC2_Cam.PCO_GetStorageMode.argtypes = [C.c_void_p,
                                                    C.c_uint16]

        storage_mode = {'recorder': 0, 'fifo': 1}
        wStorageMode = C.c_uint16(storage_mode[mode])

        start_time = time.time()
        error = self.SC2_Cam.PCO_SetStorageMode(self.camera_handle,
                                                wStorageMode)

        inp = {}
        inp.update({'storage mode': mode})

        self.log(sys._getframe().f_code.co_name, error, inp, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)

    # -------------------------------------------------------------------------
    # 2.7.7 PCO_GetRecorderSubmode
    # -------------------------------------------------------------------------
    def get_recorder_submode(self):
        """
        This function returns the current recorder submode of the camera.
        Recorder submode is only available if the storage mode is set to
        [recorder]. Recorder submode is either [sequence] or [ring buffer].
        """

        self.SC2_Cam.PCO_GetRecorderSubmode.argtypes = [C.c_void_p,
                                                        C.POINTER(C.c_uint16)]

        wRecSubmode = C.c_uint16()

        start_time = time.time()
        error = self.SC2_Cam.PCO_GetRecorderSubmode(self.camera_handle,
                                                    wRecSubmode)

        ret = {}
        if error == 0:
            submode = {0: 'sequence', 1: 'ring buffer'}
            ret.update({'recorder submode': submode[wRecSubmode.value]})

        self.log(sys._getframe().f_code.co_name, error, ret, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)
        return ret

    # -------------------------------------------------------------------------
    # 2.7.8 PCO_SetRecorderSubmode
    # -------------------------------------------------------------------------
    def set_recorder_submode(self, submode):
        """
        This function sets the recorder submode of the camera. Recorder submode
        is only available if PCO_SetStorageMode is set to [recorder]. Recorder
        submode can be set to [sequence] or [ring buffer].
        """

        self.SC2_Cam.PCO_SetRecorderSubmode.argtypes = [C.c_void_p,
                                                        C.c_uint16]

        recorder_submode = {'sequence': 0, 'ring buffer': 1}
        wRecSubmode = C.c_uint16(recorder_submode[submode])

        start_time = time.time()
        error = self.SC2_Cam.PCO_SetRecorderSubmode(self.camera_handle,
                                                    wRecSubmode)

        inp = {}
        inp.update({'recorder submode': submode})

        self.log(sys._getframe().f_code.co_name, error, inp, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)

    # -------------------------------------------------------------------------
    # 2.7.9 PCO_GetAcquireMode
    # -------------------------------------------------------------------------
    def get_acquire_mode(self):
        """
        This function returns the current acquire mode of the camera. Acquire
        mode can be either [auto], [external] or [external modulate].
        """

        self.SC2_Cam.PCO_GetAcquireMode.argtypes = [C.c_void_p,
                                                    C.POINTER(C.c_uint16)]

        wAcquMode = C.c_uint16()

        start_time = time.time()
        error = self.SC2_Cam.PCO_GetAcquireMode(self.camera_handle,
                                                wAcquMode)

        ret = {}
        if error == 0:
            mode = {0: 'auto', 1: 'external', 2: 'external modulated'}
            ret.update({'acquire mode': mode[wAcquMode.value]})

        self.log(sys._getframe().f_code.co_name, error, ret, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)
        return ret

    # -------------------------------------------------------------------------
    # 2.7.10 PCO_SetAcquireMode
    # -------------------------------------------------------------------------
    def set_acquire_mode(self, mode):
        """
        This function sets the acquire mode of the camera. Acquire mode can be
        either [auto], [external] or [external modulate].

        :param state: str

            * 'auto'
            * 'off'

        >>> set_acquire_mode('auto')

        >>> set_acquire_mode('external')

        >>> set_acquire_mode('external modulated')

        """

        self.SC2_Cam.PCO_GetAcquireMode.argtypes = [C.c_void_p,
                                                    C.c_uint16]

        acquire_mode = {'auto': 0,
                        'external': 1,
                        'external modulated': 2}
        wAcquMode = C.c_uint16(acquire_mode[mode])

        start_time = time.time()
        error = self.SC2_Cam.PCO_SetAcquireMode(self.camera_handle,
                                                wAcquMode)

        inp = {}
        inp.update({'acquire mode': mode})

        self.log(sys._getframe().f_code.co_name, error, inp, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)

    # -------------------------------------------------------------------------
    # 2.7.11 PCO_GetAcquireModeEx
    # -------------------------------------------------------------------------
    def get_acquire_mode_ex(self):
        """
        This function returns the current acquire mode of the camera. Acquire
        mode can be either [auto], [external], [external modulate] or
        [sequence trigger]. This function is an extended version of the
        PCO_GetAcquireMode function with an additional parameter
        dwNumberImages, which is needed for the [sequence trigger] mode.

        >>> get_acquire_mode_ex()
        {'acquire mode ex': 'auto', 'number of images': 0}

        >>> get_acquire_mode_ex()
        {'acquire mode ex': 'external', 'number of images': 0}

        >>> get_acquire_mode_ex()
        {'acquire mode ex': 'external modulated', 'number of images': 0}

        >>> get_acquire_mode_ex()
        {'acquire mode ex': 'sequence trigger', 'number of images': 100}


        """

        self.SC2_Cam.PCO_GetAcquireModeEx.argtypes = [C.c_void_p,
                                                      C.POINTER(C.c_uint16),
                                                      C.POINTER(C.c_uint32),
                                                      C.POINTER(C.c_uint32)]

        wAcquMode = C.c_uint16()
        dwNumberImages = C.c_uint32()
        dwReserved = C.c_uint32()

        start_time = time.time()
        error = self.SC2_Cam.PCO_GetAcquireModeEx(self.camera_handle,
                                                  wAcquMode,
                                                  dwNumberImages,
                                                  dwReserved)

        ret = {}
        if error == 0:
            acquire_mode_ex = {0: 'auto',
                               1: 'external',
                               2: 'external modulated',
                               4: 'sequence trigger'}
            ret.update({'acquire mode ex': acquire_mode_ex[wAcquMode.value]})
            ret.update({'number of images': dwNumberImages.value})

        self.log(sys._getframe().f_code.co_name, error, ret, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)
        return ret

    # -------------------------------------------------------------------------
    # 2.7.12 PCO_SetAcquireModeEx
    # -------------------------------------------------------------------------
    def set_acquire_mode_ex(self, mode, number_of_images=0):
        """
        This function sets the acquire mode of the camera. Acquire mode can be
        either [auto], [external], [external modulate] or [sequence trigger].
        This function is an extended version of the PCO_SetAcquireMode
        function with an additional parameter dwNumberImages, which is needed
        for the [sequence trigger] mode.

        >>> set_acquire_mode_ex('auto')

        >>> set_acquire_mode_ex('auto', 0)

        >>> set_acquire_mode_ex('external')

        >>> set_acquire_mode_ex('external modulated')

        >>> set_acquire_mode_ex('sequence trigger', 100)

        """

        self.SC2_Cam.PCO_SetAcquireModeEx.argtypes = [C.c_void_p,
                                                      C.c_uint16,
                                                      C.c_uint32,
                                                      C.POINTER(C.c_uint32)]

        acquire_mode_ex = {'auto': 0,
                           'external': 1,
                           'external modulated': 2,
                           'sequence trigger': 4}
        wAcquMode = C.c_uint16(acquire_mode_ex[mode])
        dwNumberImages = C.c_uint32(number_of_images)
        dwReserved = C.c_uint32()

        start_time = time.time()
        error = self.SC2_Cam.PCO_SetAcquireModeEx(self.camera_handle,
                                                  wAcquMode,
                                                  dwNumberImages,
                                                  dwReserved)

        inp = {}
        inp.update({'acquire mode': mode})
        inp.update({'number of images': number_of_images})

        self.log(sys._getframe().f_code.co_name, error, inp, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)


    # -------------------------------------------------------------------------
    # 2.7.13 PCO_GetAcqEnblSignalStatus
    # -------------------------------------------------------------------------
    def get_acquire_enable_signal_status(self):
        """


        :return: {'acquire enable signal status': str}
        :rtype: dict
        """

        self.SC2_Cam.PCO_GetAcqEnblSignalStatus.argtypes = [C.c_void_p,
                                                            C.POINTER(C.c_uint16)]

        wAcquireEnableSignalStatus = C.c_uint16()

        start_time = time.time()
        error = self.SC2_Cam.PCO_GetAcqEnblSignalStatus(self.camera_handle,
                                                        wAcquireEnableSignalStatus)

        ret = {}
        if error == 0:
            acquire_enable_signal_status = {0: 'false', 1: 'true'}
            ret.update({'acquire enable signal status': acquire_enable_signal_status[wAcquireEnableSignalStatus.value]})

        self.log(sys._getframe().f_code.co_name, error, ret, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)
        return ret

    # -------------------------------------------------------------------------
    # 2.7.14 PCO_GetMetaDataMode
    # -------------------------------------------------------------------------
    def get_metadata_mode(self):
        """
        Get metadata mode

        :return: {'metadata mode': str}
        :rtype: dict
        """

        self.SC2_Cam.PCO_GetMetaDataMode.argtypes = [C.c_void_p,
                                                     C.POINTER(C.c_uint16),
                                                     C.POINTER(C.c_uint16),
                                                     C.POINTER(C.c_uint16)]

        wMetaDataMode = C.c_uint16()
        wMetaDataSize = C.c_uint16()
        wMetaDataVersion = C.c_uint16()

        start_time = time.time()
        error = self.SC2_Cam.PCO_GetMetaDataMode(self.camera_handle,
                                                 wMetaDataMode,
                                                 wMetaDataSize,
                                                 wMetaDataVersion)

        ret = {}
        if error == 0:
            metadata_mode = {0: 'off',
                             1: 'on'}
            ret.update({'metadata mode': metadata_mode[wMetaDataMode.value]})

        self.log(sys._getframe().f_code.co_name, error, ret, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)
        return ret

    # -------------------------------------------------------------------------
    # 2.7.15 PCO_SetMetaDataMode
    # -------------------------------------------------------------------------
    def set_metadata_mode(self, mode):
        """
        :param mode: str

            * 'on'
            * 'off'
        """

        self.SC2_Cam.PCO_SetMetaDataMode.argtypes = [C.c_void_p,
                                                     C.c_uint16,
                                                     C.POINTER(C.c_uint16),
                                                     C.POINTER(C.c_uint16)]

        metadata_mode = {'off': 0,
                         'on': 1}
        wMetaDataSize = C.c_uint16()
        wMetaDataVersion = C.c_uint16()

        start_time = time.time()
        error = self.SC2_Cam.PCO_SetMetaDataMode(self.camera_handle,
                                                 metadata_mode[mode],
                                                 wMetaDataSize,
                                                 wMetaDataVersion)

        inp = {}
        inp.update({'meta data mode': mode})

        self.log(sys._getframe().f_code.co_name, error, inp, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)

    # -------------------------------------------------------------------------
    # 2.7.16 PCO_GetRecordStopEvent
    # -------------------------------------------------------------------------
    def get_record_stop_event(self):
        """
        This function returns the current record stop event mode and the number
        of images, which will be recorded after a recorder stop event is
        triggered. The record stop event mode is only valid, if storage mode is
        [recorder] and recorder submode is [ring buffer].
        """

        self.SC2_Cam.PCO_GetRecordStopEvent.argtypes = [C.c_void_p,
                                                        C.POINTER(C.c_uint16),
                                                        C.POINTER(C.c_uint32)]

        wRecordStopEventMode = C.c_uint16()
        dwRecordStopDelayImages = C.c_uint32()

        start_time = time.time()
        error = self.SC2_Cam.PCO_GetRecordStopEvent(self.camera_handle,
                                                    wRecordStopEventMode,
                                                    dwRecordStopDelayImages)

        ret = {}
        if error == 0:
            mode = {0: 'off', 1: 'software', 2: 'extern'}
            ret.update({'record stop event  mode': mode[wRecordStopEventMode.value]})
            ret.update({'record stop delay images': dwRecordStopDelayImages.value})

        self.log(sys._getframe().f_code.co_name, error, ret, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)
        return ret

    # -------------------------------------------------------------------------
    # 2.7.17 PCO_SetRecordStopEvent
    # -------------------------------------------------------------------------
    def set_record_stop_event(self, record_stop_event_mode, record_stop_delay_images):
        """
        """

        self.SC2_Cam.PCO_SetRecordStopEvent.argtypes = [C.c_void_p,
                                                        C.c_uint16,
                                                        C.c_uint32]

        mode = {'off': 0, 'software': 1, 'extern': 2}
        wRecordStopEventMode = C.c_uint16(mode[record_stop_event_mode])
        dwRecordStopDelayImages = C.c_uint32(record_stop_delay_images)

        start_time = time.time()
        error = self.SC2_Cam.PCO_SetRecordStopEvent(self.camera_handle,
                                                    wRecordStopEventMode,
                                                    dwRecordStopDelayImages)

        inp = {}
        inp.update({'record stop event  mode': record_stop_event_mode})
        inp.update({'record stop delay images': record_stop_delay_images})

        self.log(sys._getframe().f_code.co_name, error, inp, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)

    # -------------------------------------------------------------------------
    # 2.7.18 PCO_StopRecord
    # -------------------------------------------------------------------------
    def stop_record(self):
        """
        """

        self.SC2_Cam.PCO_StopRecord.argtypes = [C.c_void_p,
                                                C.POINTER(C.c_uint16),
                                                C.POINTER(C.c_uint32)]

        wReserved0 = C.c_uint16()
        dwReserved1 = C.c_uint32()

        start_time = time.time()
        error = self.SC2_Cam.PCO_StopRecord(self.camera_handle,
                                            wReserved0,
                                            dwReserved1)

        self.log(sys._getframe().f_code.co_name, error, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)

    # -------------------------------------------------------------------------
    # 2.7.19 PCO_SetDateTime
    # -------------------------------------------------------------------------
    def set_date_time(self, year, month, day, hour, minute, second):
        """

        """

        self.SC2_Cam.PCO_SetDateTime.argtypes = [C.c_void_p,
                                                 C.c_uint8,
                                                 C.c_uint8,
                                                 C.c_uint16,
                                                 C.c_uint16,
                                                 C.c_uint8,
                                                 C.c_uint8]

        ucDay = C.c_uint8(day)
        ucMonth = C.c_uint8(month)
        wYear = C.c_uint16(year)
        wHour = C.c_uint16(hour)
        ucMin = C.c_uint8(minute)
        ucSec = C.c_uint8(second)

        start_time = time.time()
        error = self.SC2_Cam.PCO_SetDateTime(self.camera_handle,
                                             ucDay,
                                             ucMonth,
                                             wYear,
                                             wHour,
                                             ucMin,
                                             ucSec)

        inp = {}
        inp.update({'year': year,
                    'month': month,
                    'day': day,
                    'hour': hour,
                    'minute': minute,
                    'second': second})

        self.log(sys._getframe().f_code.co_name, error, inp, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)

    # -------------------------------------------------------------------------
    # 2.7.20 PCO_GetTimestampMode
    # -------------------------------------------------------------------------
    def get_timestamp_mode(self):
        """
        Returns the current timestamp mode of the camera.

        :return: {'timestamp mode': str}
        :rtype: dict

        >>> get_timestamp_mode()
        {'timestamp mode': 'off'}

        >>> get_timestamp_mode()
        {'timestamp mode': 'binary'}

        >>> get_timestamp_mode()
        {'timestamp mode': 'binary & ascii'}

        >>> get_timestamp_mode()
        {'timestamp mode': 'ascii'}

        """

        self.SC2_Cam.PCO_GetTimestampMode.argtypes = [C.c_void_p,
                                                      C.POINTER(C.c_uint16)]

        wTimeStampMode = C.c_uint16()

        start_time = time.time()
        error = self.SC2_Cam.PCO_GetTimestampMode(self.camera_handle,
                                                  wTimeStampMode)

        ret = {}
        if error == 0:
            timestamp_mode = {0: 'off',
                              1: 'binary',
                              2: 'binary & ascii',
                              3: 'ascii'}
            ret.update({'timestamp mode': timestamp_mode[wTimeStampMode.value]})

        self.log(sys._getframe().f_code.co_name, error, ret, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)
        return ret

    # -------------------------------------------------------------------------
    # 2.7.21 PCO_SetTimestampMode
    # -------------------------------------------------------------------------
    def set_timestamp_mode(self, mode):
        """
        Set timestamp mode


        :param mode: str

            * 'off'
            * 'binary'
            * 'binary & ascii'
            * 'ascii'
        """

        self.SC2_Cam.PCO_SetTimestampMode.argtypes = [C.c_void_p,
                                                      C.c_uint16]

        timestamp_mode = {'off': 0,
                          'binary': 1,
                          'binary & ascii': 2,
                          'ascii': 3}

        start_time = time.time()
        error = self.SC2_Cam.PCO_SetTimestampMode(self.camera_handle,
                                                  timestamp_mode[mode])

        inp = {}
        inp.update({'timestamp mode': mode})

        self.log(sys._getframe().f_code.co_name, error, inp, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)

    # -------------------------------------------------------------------------
    # 2.8.1 PCO_GetStorageStruct
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # 2.8.2 PCO_SetStorageStruct
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # 2.8.3 PCO_GetCameraRamSize
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # 2.8.4 PCO_GetCameraRamSegmentSize
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # 2.8.5 PCO_SetCameraRamSegmentSize
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # 2.8.6 PCO_ClearRamSegment
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # 2.8.7 PCO_GetActiveRamSegment
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # 2.8.8 PCO_SetActiveRamSegment
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # 2.9.1 PCO_GetImageStruct
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # 2.9.2 PCO_GetSegmentStruct
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # 2.9.3 PCO_GetSegmentImageSettings
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # 2.9.4 PCO_GetNumberOfImagesInSegment
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # 2.9.5 PCO_GetBitAlignment
    # -------------------------------------------------------------------------
    def get_bit_alignment(self):
        """
        Returns the bit alignment of the camera: MSB, LSB

        :return: {'bit alignment': str}
        :rtype: dict

        >>> get_bit_alignment()
        {'bit alignment': 'MSB'}

        >>> get_bit_alignment()
        {'bit alignment': 'LSB'}

        """

        self.SC2_Cam.PCO_GetBitAlignment.argtypes = [C.c_void_p,
                                                     C.POINTER(C.c_uint16)]

        wBitAlignment = C.c_uint16()

        start_time = time.time()
        error = self.SC2_Cam.PCO_GetBitAlignment(self.camera_handle,
                                                 wBitAlignment)

        ret = {}
        if error == 0:
            bit_alignment = {0: 'MSB', 1: 'LSB'}
            ret.update({'bit alignment': bit_alignment[wBitAlignment.value]})

        self.log(sys._getframe().f_code.co_name, error, ret, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)
        return ret

    # -------------------------------------------------------------------------
    # 2.9.6 PCO_SetBitAlignment
    # -------------------------------------------------------------------------
    def set_bit_alignment(self, alignment):
        """
        Set bit alignment

        :param alignment: str

            * 'MSB'
            * 'LSB'

        >>> set_bit_alignment('MSB')

        >>> set_bit_alignment('LSB')

        """

        self.SC2_Cam.PCO_SetBitAlignment.argtypes = [C.c_void_p,
                                                     C.c_uint16]

        bit_alignment = {'MSB': 0, 'LSB': 1}

        start_time = time.time()
        error = self.SC2_Cam.PCO_SetBitAlignment(self.camera_handle,
                                                 bit_alignment[alignment])

        inp = {}
        inp.update({'bit alignment': alignment})

        self.log(sys._getframe().f_code.co_name, error, inp, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)

    # -------------------------------------------------------------------------
    # 2.9.7 PCO_GetHotPixelCorrectionMode
    # -------------------------------------------------------------------------
    def get_hot_pixel_correction_mode(self):
        """
        Returns the current hot pixel correction mode of the camera.

        :return: {'hot pixel correction mode': str}
        :rtype: dict

        >>> get_hot_pixel_correction_mode()
        {'hot pixel correction mode': 'off'}

        >>> get_hot_pixel_correction_mode()
        {'hot pixel correction mode': 'on'}

        """

        self.SC2_Cam.PCO_GetHotPixelCorrectionMode.argtypes = [C.c_void_p,
                                                               C.POINTER(C.c_uint16)]

        wHotPixelCorrectionMode = C.c_uint16()

        start_time = time.time()
        error = self.SC2_Cam.PCO_GetHotPixelCorrectionMode(self.camera_handle,
                                                           wHotPixelCorrectionMode)

        ret = {}
        if error == 0:
            hot_pixel_correction_mode = {0: 'off', 1: 'on'}
            ret.update({'hot pixel correction mode': hot_pixel_correction_mode[wHotPixelCorrectionMode.value]})

        self.log(sys._getframe().f_code.co_name, error, ret, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)
        return ret

    # -------------------------------------------------------------------------
    # 2.9.8 PCO_SetHotPixelCorrectionMode
    # -------------------------------------------------------------------------
    def set_hot_pixel_correction_mode(self, mode):
        """
        Set the hot pixel correction mode.

        :param mode:
            * 'off': disables the hot pixel correction
            * 'on': enables the hot pixel correction

        >>> set_hot_pixel_correction_mode('on')

        >>> set_hot_pixel_correction_mode('off')

        """

        self.SC2_Cam.PCO_SetHotPixelCorrectionMode.argtypes = [C.c_void_p,
                                                               C.c_uint16]

        hot_pixel_correction_mode = {'off': 0, 'on': 1}

        start_time = time.time()
        error = self.SC2_Cam.PCO_SetHotPixelCorrectionMode(self.camera_handle,
                                                           hot_pixel_correction_mode[mode])

        inp = {}
        inp.update({'hot pixel correction mode': mode})

        self.log(sys._getframe().f_code.co_name, error, inp, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)

    # -------------------------------------------------------------------------
    # 2.10.1 PCO_AllocateBuffer
    # 2.10.2 PCO_FreeBuffer
    # 2.10.3 PCO_GetBufferStatus
    # 2.10.4 PCO_GetBuffer
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # 2.11.1 PCO_GetImageEx
    # 2.11.2 PCO_GetImage                                            (obsolete)
    # 2.11.3 PCO_AddBufferEx
    # 2.11.4 PCO_AddBuffer                                           (obsolete)
    # 2.11.5 PCO_AddBufferExtern
    # 2.11.6 PCO_CancelImages
    # 2.11.7 PCO_RemoveBuffer                                        (obsolete)
    # 2.11.8 PCO_GetPendingBuffer
    # 2.11.9 PCO_WaitforBuffer
    # 2.11.10 PCO_EnableSoftROI               (not recommended for new designs)
    # 2.11.11 PCO_GetMetaData                 (not recommended for new designs)
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # 2.12.1 PCO_GetTransferParameter
    # -------------------------------------------------------------------------
    def get_transfer_parameter(self):
        """

        """

        self.SC2_Cam.PCO_GetTransferParameter.argtypes = [C.c_void_p,
                                                          C.c_void_p,
                                                          C.c_int]

        buffer = (C.c_uint8 * 80)(0)
        p_buffer = C.cast(buffer, C.POINTER(C.c_void_p))
        ilen = C.c_int(len(buffer))

        start_time = time.time()
        error = self.SC2_Cam.PCO_GetTransferParameter(self.camera_handle,
                                                      p_buffer,
                                                      ilen)

        ret = {}
        if error == 0:
            ret.update({'buffer': buffer})
            ret.update({'length': ilen})

        self.log(sys._getframe().f_code.co_name, error, ret, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)
        return ret

    # -------------------------------------------------------------------------
    # 2.12.2 PCO_SetTransferParameter
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # 2.13.1 PCO_GetSensorSignalStatus                               (pco.edge)
    # -------------------------------------------------------------------------
    def get_sensor_signal_status(self):
        """
        Get sensor signal status.

        :return: {'status': int,
                  'image count': int}
        :rtype: dict
        """

        self.SC2_Cam.PCO_GetSensorSignalStatus.argtypes = [C.c_void_p,
                                                           C.POINTER(C.c_uint32),
                                                           C.POINTER(C.c_uint32),
                                                           C.POINTER(C.c_uint32),
                                                           C.POINTER(C.c_uint32)]

        dwStatus = C.c_uint32()
        dwImageCount = C.c_uint32()
        dwReserved1 = C.c_uint32()
        dwReserved2 = C.c_uint32()

        start_time = time.time()
        error = self.SC2_Cam.PCO_GetSensorSignalStatus(self.camera_handle,
                                                       dwStatus,
                                                       dwImageCount,
                                                       dwReserved1,
                                                       dwReserved2)

        ret = {}
        if error == 0:
            ret.update({'status': dwStatus.value})
            ret.update({'image count': dwImageCount.value})

        self.log(sys._getframe().f_code.co_name, error, ret, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)
        return ret

    # -------------------------------------------------------------------------
    # 2.13.2 PCO_GetCmosLineTiming                                   (pco.edge)
    # -------------------------------------------------------------------------
    def get_cmos_line_timing(self):

        self.SC2_Cam.PCO_GetCmosLineTiming.argtypes = [C.c_void_p,
                                                       C.POINTER(C.c_uint16),
                                                       C.POINTER(C.c_uint16),
                                                       C.POINTER(C.c_uint32),
                                                       C.POINTER(C.c_uint32),
                                                       C.c_uint16]

        wParameter = C.c_uint16()
        wTimebase = C.c_uint16()
        dwLineTime = C.c_uint32()
        dwReserved = C.c_uint32()
        wReservedLen = C.c_uint16()

        start_time = time.time()
        error = self.SC2_Cam.PCO_GetCmosLineTiming(self.camera_handle,
                                                   wParameter,
                                                   wTimebase,
                                                   dwLineTime,
                                                   dwReserved,
                                                   wReservedLen)

        ret = {}
        if error == 0:

            parameter = {0: 'off', 1: 'on'}
            ret.update({'parameter': parameter[wParameter.value]})

            timebase = {0: 1e-9, 1: 1e-6, 2: 1e-3}
            line_time = timebase[wTimebase.value] * dwLineTime.value
            ret.update({'line time': line_time})

        self.log(sys._getframe().f_code.co_name, error, ret, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)
        return ret

    # -------------------------------------------------------------------------
    # 2.13.3 PCO_SetCmosLineTiming                                   (pco.edge)
    # -------------------------------------------------------------------------
    def set_cmos_line_timing(self, parameter, line_time):

        self.SC2_Cam.PCO_SetCmosLineTiming.argtypes = [C.c_void_p,
                                                       C.c_uint16,
                                                       C.c_uint16,
                                                       C.c_uint32,
                                                       C.c_uint32,
                                                       C.c_uint16]

        if line_time <= 4.0:
            linetime = int(line_time * 1e9)
            timebase = 'ns'
        else :
            linetime = int(line_time * 1e6)
            timebase = 'us'

        parameter_dict = {'off': 0, 'on': 1}
        timebase_dict = {'ns': 0, 'us': 1, 'ms': 2}

        wParameter = C.c_uint16(parameter_dict[parameter])
        wTimebase = C.c_uint16(timebase_dict[timebase])
        dwLineTime = C.c_uint32(linetime)
        dwReserved = C.c_uint32(0)
        wReservedLen = C.c_uint16(0)

        start_time = time.time()
        error = self.SC2_Cam.PCO_SetCmosLineTiming(self.camera_handle,
                                                   wParameter,
                                                   wTimebase,
                                                   dwLineTime,
                                                   dwReserved,
                                                   wReservedLen)

        inp = {}
        inp.update({'parameter': parameter})
        inp.update({'timebase': timebase})
        inp.update({'line time': linetime})

        self.log(sys._getframe().f_code.co_name, error, inp, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)

    # -------------------------------------------------------------------------
    # 2.13.4 PCO_GetCmosLineExposureDelay                            (pco.edge)
    # -------------------------------------------------------------------------
    def get_cmos_line_exposure_delay(self):

        self.SC2_Cam.PCO_GetCmosLineExposureDelay.argtypes = [C.c_void_p,
                                                              C.POINTER(C.c_uint32),
                                                              C.POINTER(C.c_uint32),
                                                              C.POINTER(C.c_uint32),
                                                              C.c_uint16]
        dwExposureLines = C.c_uint32()
        dwDelayLines = C.c_uint32()
        dwReserved = C.c_uint32()
        wReservedLen = C.c_uint16(0)

        start_time = time.time()
        error = self.SC2_Cam.PCO_GetCmosLineExposureDelay(self.camera_handle,
                                                          dwExposureLines,
                                                          dwDelayLines,
                                                          dwReserved,
                                                          wReservedLen)
        ret = {}
        if error == 0:
            ret.update({'lines exposure': dwExposureLines.value})
            ret.update({'lines delay': dwDelayLines.value})

        self.log(sys._getframe().f_code.co_name, error, ret, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)
        return ret

    # -------------------------------------------------------------------------
    # 2.13.5 PCO_SetCmosLineExposureDelay                            (pco.edge)
    # -------------------------------------------------------------------------
    def set_cmos_line_exposure_delay(self, lines_exposure, lines_delay):

        self.SC2_Cam.PCO_SetCmosLineExposureDelay.argtypes = [C.c_void_p,
                                                              C.c_uint32,
                                                              C.c_uint32,
                                                              C.POINTER(C.c_uint32),
                                                              C.c_uint16]
        dwExposureLines = C.c_uint32(lines_exposure)
        dwDelayLines = C.c_uint32(lines_delay)
        dwReserved = C.c_uint32()
        wReservedLen = C.c_uint16(0)

        start_time = time.time()
        error = self.SC2_Cam.PCO_SetCmosLineExposureDelay(self.camera_handle,
                                                          dwExposureLines,
                                                          dwDelayLines,
                                                          dwReserved,
                                                          wReservedLen)

        inp = {}
        inp.update({'lines exposure ': lines_exposure})
        inp.update({'lines delay': lines_delay})

        self.log(sys._getframe().f_code.co_name, error, inp, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)


    # -------------------------------------------------------------------------
    # 2.13.6 PCO_SetTransferParametersAuto                           (pco.edge)
    # -------------------------------------------------------------------------
    def set_transfer_parameters_auto(self, buffer):
        """

        """

        self.SC2_Cam.PCO_SetTransferParametersAuto.argtypes = [C.c_void_p,
                                                               C.c_void_p,
                                                               C.c_int]

        p_buffer = C.cast(buffer, C.POINTER(C.c_void_p))
        ilen = C.c_int(len(buffer))

        start_time = time.time()
        error = self.SC2_Cam.PCO_SetTransferParametersAuto(self.camera_handle,
                                                           p_buffer,
                                                           ilen)

        self.log(sys._getframe().f_code.co_name, error, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)

    # -------------------------------------------------------------------------
    # 2.13.7 PCO_GetInterfaceOutputFormat                            (pco.edge)
    # -------------------------------------------------------------------------
    def get_interface_output_format(self, interface):
        """
        :param interface: str

            * 'edge'
        :return: {'format': int}
        :rtype: dict
        """

        self.SC2_Cam.PCO_GetInterfaceOutputFormat.argtypes = [C.c_void_p,
                                                              C.POINTER(C.c_uint16),
                                                              C.POINTER(C.c_uint16),
                                                              C.POINTER(C.c_uint16),
                                                              C.POINTER(C.c_uint16)]

        interface_types = {'edge': 0x0002}

        wDestInterface = C.c_uint16(interface_types[interface])
        wFormat = C.c_uint16()
        wReserved1 = C.c_uint16()
        wReserved2 = C.c_uint16()

        start_time = time.time()
        error = self.SC2_Cam.PCO_GetInterfaceOutputFormat(self.camera_handle,
                                                          wDestInterface,
                                                          wFormat,
                                                          wReserved1,
                                                          wReserved2)

        ret = {}
        if error == 0:
            ret.update({'format': wFormat.value})

        self.log(sys._getframe().f_code.co_name, error, ret, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)
        return ret

    # -------------------------------------------------------------------------
    # 2.13.8 PCO_SetInterfaceOutputFormat                            (pco.edge)
    # -------------------------------------------------------------------------
    def set_interface_output_format(self,
                                    interface,
                                    format):
        """
        Set interface output format

        :param interface: set interfcae parameter to 'edge' for changing the
            readout direction of the SCMOS image sensor
        :param format:

            * SCCMOS_FORMAT_TOP_CENTER_BOTTOM_CENTER
            * SCCMOS_FORMAT_CENTER_TOP_CENTER_BOTTOM
            * SCCMOS_FORMAT_CENTER_TOP_BOTTOM_CENTER
            * SCCMOS_FORMAT_TOP_CENTER_CENTER_BOTTOM
            * SCCMOS_FORMAT_TOP_BOTTOM
        """

        self.SC2_Cam.PCO_SetInterfaceOutputFormat.argtypes = [C.c_void_p,
                                                              C.c_uint16,
                                                              C.c_uint16,
                                                              C.c_uint16,
                                                              C.c_uint16]

        interface_types = {'edge': 0x0002}
        output_format_types = {'top bottom': 0x0000,
                               'top center bottom center': 0x0100,
                               'center top center bottom': 0x0200,
                               'center top bottom center': 0x0300,
                               'top center center bottom': 0x0400}

        wDestInterface = C.c_uint16(interface_types[interface])
        wFormat = C.c_uint16(output_format_types[format])
        wReserved1 = C.c_uint16()
        wReserved2 = C.c_uint16()

        start_time = time.time()
        error = self.SC2_Cam.PCO_SetInterfaceOutputFormat(self.camera_handle,
                                                          wDestInterface,
                                                          wFormat,
                                                          wReserved1,
                                                          wReserved2)

        inp = {}
        inp.update({'interface': interface,
                    'output format': format})

        self.log(sys._getframe().f_code.co_name, error, inp, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)

    # -------------------------------------------------------------------------
    # 2.14.1 PCO_GetImageTransferMode                               (pco.dimax)
    # 2.14.2 PCO_SetImageTransferMode                               (pco.dimax)
    # 2.14.3 PCO_GetCDIMode                                         (pco.dimax)
    # 2.14.4 PCO_SetCDIMode                                         (pco.dimax)
    # 2.14.5 PCO_GetPowerSaveMode                                   (pco.dimax)
    # 2.14.6 PCO_SetPowerSaveMode                                   (pco.dimax)
    # 2.14.7 PCO_GetBatteryStatus                                   (pco.dimax)
    # -------------------------------------------------------------------------
    # 2.15.1 PCO_GetInterfaceOutputFormat                (pco.dimax with HDSDI)
    # 2.15.2 PCO_SetInterfaceOutputFormat                (pco.dimax with HDSDI)
    # 2.15.3 PCO_PlayImagesFromSegmentHDSDI              (pco.dimax with HDSDI)
    # 2.15.4 PCO_GetPlayPositionHDSDI                    (pco.dimax with HDSDI)
    # 2.15.5 PCO_GetColorSettings                        (pco.dimax with HDSDI)
    # 2.15.6 PCO_SetColorSettings                        (pco.dimax with HDSDI)
    # 2.15.7 PCO_DoWhiteBalance                          (pco.dimax with HDSDI)

    # -------------------------------------------------------------------------
    # 2.16.1 PCO_GetFlimModulationParameter
    # -------------------------------------------------------------------------
    def get_flim_modulation_parameter(self):
        """
        :return: {'source select': str,
                'output waveform': str}
        :rtype: dict

        >>> get_flim_modulation_parameter()
        {'source select': 'intern', 'output waveform': 'sinusoidal'}

        """

        self.SC2_Cam.PCO_GetFlimModulationParameter.argtypes = [C.c_void_p,
                                                                C.POINTER(C.c_uint16),
                                                                C.POINTER(C.c_uint16),
                                                                C.POINTER(C.c_uint16),
                                                                C.POINTER(C.c_uint16)]

        wSourceSelect = C.c_uint16()
        wOutputWaveform = C.c_uint16()
        wReserved1 = C.c_uint16()
        wReserved2 = C.c_uint16()

        start_time = time.time()
        error = self.SC2_Cam.PCO_GetFlimModulationParameter(self.camera_handle,
                                                            wSourceSelect,
                                                            wOutputWaveform,
                                                            wReserved1,
                                                            wReserved2)

        ret = {}
        if error == 0:
            source_select = {0: 'intern', 1: 'extern'}
            ret.update({'source select': source_select[wSourceSelect.value]})
            output_waveform = {0: 'none', 1: 'sinusoidal', 2: 'rectangular'}
            ret.update({'output waveform': output_waveform[wOutputWaveform.value]})

        self.log(sys._getframe().f_code.co_name, error, ret, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)
        return ret

    # -------------------------------------------------------------------------
    # 2.16.2 PCO_SetFlimModulationParameter
    # -------------------------------------------------------------------------
    def set_flim_modulation_parameter(self, source_select_mode, output_waveform_mode):
        """
        :param source_select_mode: str

            * 'intern'
            * 'extern'
        :param output_waveform_mode: str

            * 'none'
            * 'sinusoidal'
            * 'rectangular'
        """

        self.SC2_Cam.PCO_SetFlimModulationParameter.argtypes = [C.c_void_p,
                                                                C.c_uint16,
                                                                C.c_uint16,
                                                                C.c_uint16,
                                                                C.c_uint16]

        source_select = {'intern': 0, 'extern': 1}
        output_waveform = {'none': 0, 'sinusoidal': 1, 'rectangular': 2}
        wReserved1 = C.c_uint16(0)
        wReserved2 = C.c_uint16(0)

        start_time = time.time()
        error = self.SC2_Cam.PCO_SetFlimModulationParameter(self.camera_handle,
                                                            source_select[source_select_mode],
                                                            output_waveform[output_waveform_mode],
                                                            wReserved1,
                                                            wReserved2)

        inp = {}
        inp.update({'source select mode': source_select_mode,
                    'output waveform mode': output_waveform_mode})

        self.log(sys._getframe().f_code.co_name, error, inp, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)

    # -------------------------------------------------------------------------
    # 2.16.3 PCO_GetFlimMasterModulationFrequency
    # -------------------------------------------------------------------------
    def get_flim_master_modulation_frequency(self):
        """
        Get flim modulation frequency

        :return: {'frequency': int}
        :rtype: dict
        """

        self.SC2_Cam.PCO_GetFlimMasterModulationFrequency.argtypes = [C.c_void_p,
                                                                      C.POINTER(C.c_uint32)]

        dwFrequency = C.c_uint32()

        start_time = time.time()
        error = self.SC2_Cam.PCO_GetFlimMasterModulationFrequency(self.camera_handle,
                                                                  dwFrequency)

        ret = {}
        if error == 0:
            ret.update({'frequency': dwFrequency.value})

        self.log(sys._getframe().f_code.co_name, error, ret, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)
        return ret

    # -------------------------------------------------------------------------
    # 2.16.4 PCO_SetFlimMasterModulationFrequency
    # -------------------------------------------------------------------------
    def set_flim_master_modulation_frequency(self, frequency):
        """


        :param frequency: int
        """

        self.SC2_Cam.PCO_SetFlimMasterModulationFrequency.argtypes = [C.c_void_p,
                                                                      C.c_uint32]

        dwFrequency = C.c_uint32(frequency)

        start_time = time.time()
        error = self.SC2_Cam.PCO_SetFlimMasterModulationFrequency(self.camera_handle,
                                                                  dwFrequency)

        inp = {'frequency': frequency}

        self.log(sys._getframe().f_code.co_name, error, inp, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)

    # -------------------------------------------------------------------------
    # 2.16.5 PCO_GetFlimPhaseSequenceParameter
    # -------------------------------------------------------------------------
    def get_flim_phase_sequence_parameter(self):
        """
        :return: {'phase number': str,
                'phase symmetry': str,
                'phase order': str,
                'tap select': str}
        :rtype: dict
        """

        self.SC2_Cam.PCO_GetFlimPhaseSequenceParameter.argtypes = [C.c_void_p,
                                                                   C.POINTER(C.c_uint16),
                                                                   C.POINTER(C.c_uint16),
                                                                   C.POINTER(C.c_uint16),
                                                                   C.POINTER(C.c_uint16),
                                                                   C.POINTER(C.c_uint16),
                                                                   C.POINTER(C.c_uint16)]

        wPhaseNumber = C.c_uint16()
        wPhaseSymmetry = C.c_uint16()
        wPhaseOrder = C.c_uint16()
        wTapSelect = C.c_uint16()
        wReserved1 = C.c_uint16()
        wReserved2 = C.c_uint16()

        start_time = time.time()
        error = self.SC2_Cam.PCO_GetFlimPhaseSequenceParameter(self.camera_handle,
                                                               wPhaseNumber,
                                                               wPhaseSymmetry,
                                                               wPhaseOrder,
                                                               wTapSelect,
                                                               wReserved1,
                                                               wReserved2)

        ret = {}
        if error == 0:
            phase_number = {0: 'manual shifting', 1: '2 phases', 2: '4 phases', 3: '8 phases', 4: '16 phases'}
            ret.update({'phase number': phase_number[wPhaseNumber.value]})
            phase_symmetry = {0: 'singular', 1: 'twice'}
            ret.update({'phase symmetry': phase_symmetry[wPhaseSymmetry.value]})
            phase_order = {0: 'ascending', 1: 'opposite'}
            ret.update({'phase order': phase_order[wPhaseOrder.value]})
            tap_select = {0: 'both', 1: 'tap A', 2: 'tap B'}
            ret.update({'tap select': tap_select[wTapSelect.value]})

        self.log(sys._getframe().f_code.co_name, error, ret, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)
        return ret

    # -------------------------------------------------------------------------
    # 2.16.6 PCO_SetFlimPhaseSequenceParameter
    # -------------------------------------------------------------------------
    def set_flim_phase_sequence_parameter(self, phase_number_mode, phase_symmetry_mode, phase_order_mode, tap_select_mode):
        """

        """

        self.SC2_Cam.PCO_SetFlimPhaseSequenceParameter.argtypes = [C.c_void_p,
                                                                   C.c_uint16,
                                                                   C.c_uint16,
                                                                   C.c_uint16,
                                                                   C.c_uint16,
                                                                   C.c_uint16,
                                                                   C.c_uint16]

        phase_number = {'manual shifting': 0,
                        '2 phases': 1,
                        '4 phases': 2,
                        '8 phases': 3,
                        '16 phases': 4}
        phase_symmetry = {'singular': 0, 'twice': 1}
        phase_order = {'ascending': 0, 'opposite': 1}
        tap_select = {'both': 0, 'tap A': 1, 'tap B': 2}
        wReserved1 = C.c_uint16(0)
        wReserved2 = C.c_uint16(0)

        start_time = time.time()
        error = self.SC2_Cam.PCO_SetFlimPhaseSequenceParameter(self.camera_handle,
                                                               phase_number[phase_number_mode],
                                                               phase_symmetry[phase_symmetry_mode],
                                                               phase_order[phase_order_mode],
                                                               tap_select[tap_select_mode],
                                                               wReserved1,
                                                               wReserved2)

        inp = {'phase number mode': phase_number_mode,
               'phase symmetry mode': phase_symmetry_mode,
               'phase order mode': phase_order_mode,
               'tap select mode': tap_select_mode}

        self.log(sys._getframe().f_code.co_name, error, inp, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)

    # -------------------------------------------------------------------------
    # 2.16.7 PCO_GetFlimRelativePhase
    # -------------------------------------------------------------------------
    def get_flim_relative_phase(self):
        """

        """

        self.SC2_Cam.PCO_GetFlimRelativePhase.argtypes = [C.c_void_p,
                                                          C.POINTER(C.c_uint32)]

        dwPhaseMilliDeg = C.c_uint32()

        start_time = time.time()
        error = self.SC2_Cam.PCO_GetFlimRelativePhase(self.camera_handle,
                                                      dwPhaseMilliDeg)

        ret = {}
        if error == 0:
            ret.update({'phase millidegrees': dwPhaseMilliDeg.value})

        self.log(sys._getframe().f_code.co_name, error, ret, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)
        return ret

    # -------------------------------------------------------------------------
    # 2.16.8 PCO_SetFlimRelativePhase
    # -------------------------------------------------------------------------
    def set_flim_relative_phase(self, phase_millidegrees):
        """

        """

        self.SC2_Cam.PCO_SetFlimRelativePhase.argtypes = [C.c_void_p,
                                                          C.c_uint32]

        dwPhaseMilliDeg = C.c_uint32(phase_millidegrees)

        start_time = time.time()
        error = self.SC2_Cam.PCO_SetFlimRelativePhase(self.camera_handle,
                                                      dwPhaseMilliDeg)

        inp = {'phase millidegrees': phase_millidegrees}

        self.log(sys._getframe().f_code.co_name, error, inp, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)

    # -------------------------------------------------------------------------
    # 2.16.9 PCO_GetFlimImageProcessingFlow
    # -------------------------------------------------------------------------
    def get_flim_image_processing_flow(self):
        """

        """

        self.SC2_Cam.PCO_GetFlimImageProcessingFlow.argtypes = [C.c_void_p,
                                                                C.POINTER(C.c_uint16),
                                                                C.POINTER(C.c_uint16),
                                                                C.POINTER(C.c_uint16),
                                                                C.POINTER(C.c_uint16),
                                                                C.POINTER(C.c_uint16),
                                                                C.POINTER(C.c_uint16),
                                                                C.POINTER(C.c_uint16),
                                                                C.POINTER(C.c_uint16),
                                                                C.POINTER(C.c_uint16),
                                                                C.POINTER(C.c_uint16)]

        wAsymmetryCorrection = C.c_uint16()
        wCalculationMode = C.c_uint16()
        wReferencingMode = C.c_uint16()
        wThresholdLow = C.c_uint16()
        wThresholdHigh = C.c_uint16()
        wOutputMode = C.c_uint16()
        wReserved1 = C.c_uint16()
        wReserved2 = C.c_uint16()
        wReserved3 = C.c_uint16()
        wReserved4 = C.c_uint16()

        start_time = time.time()
        error = self.SC2_Cam.PCO_GetFlimImageProcessingFlow(self.camera_handle,
                                                            wAsymmetryCorrection,
                                                            wCalculationMode,
                                                            wReferencingMode,
                                                            wThresholdLow,
                                                            wThresholdHigh,
                                                            wOutputMode,
                                                            wReserved1,
                                                            wReserved2,
                                                            wReserved3,
                                                            wReserved4)

        ret = {}
        if error == 0:
            asymmetry_correction = {0: 'off', 1: 'average'}
            output_mode = {0: 'default', 1: 'multiply x2'}
            ret.update({'asymmetry correction': asymmetry_correction[wAsymmetryCorrection.value]})
            ret.update({'output mode': output_mode[wOutputMode.value]})

        self.log(sys._getframe().f_code.co_name, error, ret, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)
        return ret

    # -------------------------------------------------------------------------
    # 2.16.10 PCO_SetFlimImageProcessingFlow
    # -------------------------------------------------------------------------
    def set_flim_image_processing_flow(self, a_c_mode, o_m_mode):
        """

        """

        self.SC2_Cam.PCO_SetFlimImageProcessingFlow.argtypes = [C.c_void_p,
                                                                C.c_uint16,
                                                                C.c_uint16,
                                                                C.c_uint16,
                                                                C.c_uint16,
                                                                C.c_uint16,
                                                                C.c_uint16,
                                                                C.c_uint16,
                                                                C.c_uint16,
                                                                C.c_uint16,
                                                                C.c_uint16,]

        asymmetry_correction = {'off': 0, 'average': 1}
        output_mode = {'default': 0, 'multiply x2': 1}

        start_time = time.time()
        error = self.SC2_Cam.PCO_SetFlimImageProcessingFlow(self.camera_handle,
                                                            asymmetry_correction[a_c_mode],
                                                            0, 0, 0, 0,
                                                            output_mode[o_m_mode],
                                                            0, 0, 0, 0)

        inp = {'a c mode': a_c_mode,
               'o m mode': o_m_mode}

        self.log(sys._getframe().f_code.co_name, error, inp, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)

    # -------------------------------------------------------------------------
    # 2.17.1 PCO_InitLensControl
    # -------------------------------------------------------------------------
    def init_lens_control(self):
        """
        """

        """class PCO_LensControl(C.Structure):
            _pack_ = 1
            _fields_ = [
                ("wSize", C.c_uint16),
                ("pstrUserInterfaceInfo", C.c_void_p),
                ("pstrUserInterfaceSettings", C.c_void_p),
                ("pstrLensControlParameters", C.c_void_p),
                ("hCamera", C.c_void_p)]"""

        self.SC2_Cam.PCO_InitLensControl.argtypes = [C.c_void_p,
                                                     C.POINTER(C.c_void_p)]

        start_time = time.time()
        error = self.SC2_Cam.PCO_InitLensControl(self.camera_handle,
                                                 self.lens_control)

        self.log(sys._getframe().f_code.co_name, error, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)

    # -------------------------------------------------------------------------
    # 2.17.2 PCO_CleanupLensControl
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # 2.17.3 PCO_CloseLensControl
    # -------------------------------------------------------------------------
    def close_lens_control(self):
        """
        Closes and deletes a lens control object. The handle will be invalid
        afterwards.
        """

        self.SC2_Cam.PCO_CloseLensControl.argtypes = [C.c_void_p]

        start_time = time.time()
        error = self.SC2_Cam.PCO_CloseLensControl(self.lens_control)

        self.lens_control = C.c_void_p(0)

        self.log(sys._getframe().f_code.co_name, error, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)

    # -------------------------------------------------------------------------
    # 2.17.4 PCO_GetLensFocus
    # -------------------------------------------------------------------------
    def get_lens_focus(self):
        """
        Gets the current focus of the lens control device as value between
        0...0x3FFF.
        """

        self.SC2_Cam.PCO_GetLensFocus.argtypes = [C.c_void_p,
                                                  C.POINTER(C.c_long),
                                                  C.POINTER(C.c_uint32)]

        lFocusPos = C.c_long()
        dwflags = C.c_uint32()

        start_time = time.time()
        error = self.SC2_Cam.PCO_GetLensFocus(self.lens_control,
                                              lFocusPos,
                                              dwflags)

        ret = {}
        if error == 0:
            ret.update({'lFocusPos': lFocusPos.value})
            ret.update({'dwflags': dwflags.value})

        self.log(sys._getframe().f_code.co_name, error, ret, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)
        return ret



    # -------------------------------------------------------------------------
    # 2.17.5 PCO_SetLensFocus
    # -------------------------------------------------------------------------
    def set_lens_focus(self, focus_pos):
        """
        Sets the focus of the lens control device to a new position. Value must
        be between 0...0x3FFF.
        """

        self.SC2_Cam.PCO_SetLensFocus.argtypes = [C.c_void_p,
                                                  C.POINTER(C.c_long),
                                                  C.c_uint32,
                                                  C.POINTER(C.c_uint32)]

        lFocusPos = C.c_long(focus_pos)
        dwflagsin = C.c_uint32()
        dwflagsout = C.c_uint32()

        start_time = time.time()
        error = self.SC2_Cam.PCO_SetLensFocus(self.lens_control,
                                              lFocusPos,
                                              dwflagsin,
                                              dwflagsout)

        inp = {}
        inp.update({'focus_pos': focus_pos})
        inp.update({'dwflagsin': dwflagsin})
        inp.update({'dwflagsout': dwflagsout.value})

        self.log(sys._getframe().f_code.co_name, error, inp, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)


    # -------------------------------------------------------------------------
    # 2.17.6 PCO_GetAperture
    # -------------------------------------------------------------------------
    def get_aperture(self):
        """
        """

        self.SC2_Cam.PCO_GetAperture.argtypes = [C.c_void_p,
                                                 C.POINTER(C.c_uint16),
                                                 C.POINTER(C.c_uint32)]

        wAperturePos = C.c_uint16()
        dwflags = C.c_uint32()

        start_time = time.time()
        error = self.SC2_Cam.PCO_GetAperture(self.lens_control,
                                             wAperturePos,
                                             dwflags)

        ret = {}
        if error == 0:
            ret.update({'wAperturePos': wAperturePos.value})
            ret.update({'dwflags': dwflags.value})

        self.log(sys._getframe().f_code.co_name, error, ret, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)
        return ret



    # -------------------------------------------------------------------------
    # 2.17.7 PCO_SetAperture
    # -------------------------------------------------------------------------
    def set_aperture(self, aperture_pos):
        """
        """

        self.SC2_Cam.PCO_SetAperture.argtypes = [C.c_void_p,
                                                 C.POINTER(C.c_uint16),
                                                 C.c_uint32,
                                                 C.POINTER(C.c_uint32)]

        wAperturePos = C.c_uint16(aperture_pos)
        dwflagsin = C.c_uint32()
        dwflagsout = C.c_uint32()

        start_time = time.time()
        error = self.SC2_Cam.PCO_SetAperture(self.lens_control,
                                             wAperturePos,
                                             dwflagsin,
                                             dwflagsout)

        inp = {}
        inp.update({'aperture_pos': aperture_pos})
        inp.update({'aperture_pos': aperture_pos})
        inp.update({'aperture_pos': aperture_pos})

        self.log(sys._getframe().f_code.co_name, error, inp, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)

    # -------------------------------------------------------------------------
    # 2.17.8 PCO_GetApertureF
    # -------------------------------------------------------------------------
    def get_aperture_f(self):
        """
        """

        self.SC2_Cam.PCO_GetApertureF.argtypes = [C.c_void_p,
                                                  C.POINTER(C.c_uint32),
                                                  C.POINTER(C.c_uint16),
                                                  C.POINTER(C.c_uint32)]

        dwAperturePos = C.c_uint32()
        wAperturePos = C.c_uint16()
        dwflags = C.c_uint32()

        start_time = time.time()
        error = self.SC2_Cam.PCO_GetApertureF(self.lens_control,
                                              dwAperturePos,
                                              wAperturePos,
                                              dwflags)

        ret = {}
        if error == 0:
            ret.update({'dwAperturePos f': (dwAperturePos.value / 10.0)})
            ret.update({'wAperturePos': wAperturePos.value})
            ret.update({'dwflags': dwflags.value})

        self.log(sys._getframe().f_code.co_name, error, ret, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)
        return ret

    # -------------------------------------------------------------------------
    # 2.17.9 PCO_SetApertureF
    # -------------------------------------------------------------------------
    def set_aperture_f(self, aperture_pos):
        """
        """

        self.SC2_Cam.PCO_SetApertureF.argtypes = [C.c_void_p,
                                                  C.POINTER(C.c_uint32),
                                                  C.c_uint32,
                                                  C.POINTER(C.c_uint32)]

        aperture_pos_int = int(aperture_pos * 10)

        dwAperturePos = C.c_uint32(aperture_pos_int)
        dwflagsin = C.c_uint32()
        dwflagsout = C.c_uint32()

        start_time = time.time()
        error = self.SC2_Cam.PCO_SetApertureF(self.lens_control,
                                              dwAperturePos,
                                              dwflagsin,
                                              dwflagsout)

        inp = {}
        inp.update({'aperture_pos f': aperture_pos})

        self.log(sys._getframe().f_code.co_name, error, inp, start_time=start_time)
        if error:
            raise self.exception(sys._getframe().f_code.co_name, error)
