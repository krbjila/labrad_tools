"""
### BEGIN NODE INFO
[info]
name = andor
version = 1.0
description = 
instancename = %LABRADNODE%_andor

[startup]
cmdline = %PYTHON% %FILE%
timeout = 60

[shutdown]
message = 987654321
timeout = 5
### END NODE INFO
"""

import os, sys
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..'))
from server_tools.hardware_interface_server import HardwareInterfaceServer

from labrad.server import setting

from andor.andor import Andor, ERROR_CODE
from time import sleep

class AndorServer(HardwareInterfaceServer):
    """ Provides access to andor camera using pyandor """
    name = '%LABRADNODE%_andor'

    def initServer(self):
        global andor
        andor = Andor()
        super(AndorServer, self).initServer()
    
    def stopServer(self):
        cameras = self.get_interface_list(None)
        for camera in cameras:
            self.select_interface(None, camera)

            errf = self.cooler_off(None)
            if errf:
                print("Error turning off cooler of camera " + str(camera) + ": " + ERROR_CODE[errf])

            (errf, status) = self.get_status(None)
            if errf:
                print("Error getting status of camera " + str(camera) + ": " + ERROR_CODE[errf])

            elif ERROR_CODE[status] == 'DRV_ACQUIRING':
                errf = self.abort_acquisition(None)
                if errf:
                    print("Error aborting acquisition of camera " + str(camera) + ": " + ERROR_CODE[errf])

            errf = self.set_shutter(None, 1, 2, 0, 0)
            if errf:
                print("Error setting shutter of camera " + str(camera) + ": " + ERROR_CODE[errf])
        
        while True:
            warm = True
            for camera in cameras:
                self.select_interface(None, camera)
                (errf, temp) = self.get_temperature(None)
                if not errf and temp < -20:
                    warm = False
                    print("Waiting for camera " + str(camera) + " to warm above -20 C. Current temperature: " + str(temp) + " C.")
                    break
                elif errf:
                    print("Error getting temperature of camera " + str(camera) + ": " + ERROR_CODE[errf])
                    warm = False
                    break
            if warm:
                break
            sleep(1)

        andor.ShutDown()
        super(AndorServer, self).stopServer()

    def refresh_available_interfaces(self):
        # Get available cameras
        (errf, nCameras) = self.get_available_cameras()
        if not errf:
            print("Found " + str(nCameras) + " cameras.")
        else:
            raise(Exception("Error getting number of cameras: " + ERROR_CODE[errf]))

        for i in range(nCameras):
            handle = self.get_camera_handle(None, i)
            self.set_current_camera(None, handle)
            (errf, ser) = self.get_camera_serial_number(None)

            if not errf:
                self.interfaces[ser] = handle
                print("Camera " + str(i) + " with handle " + str(handle) + " and serial number " + str(ser) + " is available.")
            else:
                print("Error connecting to camera " + str(i) + " with handle " + str(handle) + ": " + ERROR_CODE[errf])

    def select_interface(self, c, serial):
        handle = super(AndorServer, self).select_interface(c, serial)
        self.set_current_camera(c, handle)

    @setting(10, returns='i')
    def abort_acquisition(self, c):
        andor.AbortAcquisition()
        error_code = andor.error['AbortAcquisition']
        return error_code

    @setting(11, returns='i')
    def cancel_wait(self, c):
        andor.CancelWait()
        error_code = andor.error['CancelWait']
        return error_code

    @setting(12, returns='i')
    def cooler_off(self, c):
        andor.CoolerOFF()
        error_code = andor.error['CoolerOFF']
        return error_code

    @setting(13, returns='i')
    def cooler_on(self, c):
        andor.CoolerON()
        error_code = andor.error['CoolerON']
        return error_code

    @setting(14, size='i', returns='i*i')
    def get_acquired_data(self, c, size):
        arr = andor.GetAcquiredData(size)
        error_code = andor.error['GetAcquiredData']
        return error_code, arr
    
    @setting(15, size='i', returns='i*i')
    def get_acquired_data_16(self, c, size):
        arr = andor.GetAcquiredData16(size)
        error_code = andor.error['GetAcquiredData16']
        return error_code, arr

    @setting(16, returns='iii')
    def get_acquisition_progress(self, c):
        acc, series = andor.GetAcquisitionProgress()
        error_code = andor.error['GetAcquisitionProgress']
        return error_code, acc, series

    @setting(17, returns='iiii')
    def get_acquisition_timings(self, c):
        exposure, accumulate, kinetic = andor.GetAcquisitionTimings()
        error_code = andor.error['GetAcquisitionTimings']
        return error_code, exposure, accumulate, kinetic

    @setting(18, returns='ii')
    def get_available_cameras(self, c):
        totalCameras = andor.GetAvailableCameras()
        error_code = andor.error['GetAvailableCameras']
        return error_code, totalCameras

    @setting(19, channel='i', returns='ii')
    def get_bit_depth(self, c, channel):
        depth = andor.GetBitDepth(channel)
        error_code = andor.error['GetBitDepth']
        return error_code, depth

    @setting(20, cameraIndex='i', returns='ii')
    def get_camera_handle(self, c, cameraIndex):
        cameraHandle = andor.GetCameraHandle(cameraIndex)
        error_code = andor.error['GetCameraHandle']
        return error_code, cameraHandle

    @setting(21, returns='ii')
    def get_camera_serial_number(self, c):
        number = andor.GetCameraSerialNumber()
        error_code = andor.error['GetCameraSerialNumber']
        return error_code, number

    @setting(22, returns='ii')
    def get_current_camera(self, c):
        cameraHandle = andor.GetCurrentCamera()
        error_code = andor.error['GetCurrentCamera']
        return error_code, cameraHandle

    @setting(23, returns='iii')
    def get_detector(self, c):
        xpixels, ypixels = andor.GetDetector()
        error_code = andor.error['GetDetector']
        return error_code, xpixels, ypixels

    @setting(24, returns='ii')
    def get_emccd_gain(self, c):
        gain = andor.GetEMCCDGain()
        error_code = andor.error['GetEMCCDGain']
        return error_code, gain

    @setting(25, returns='iii')
    def get_em_gain_range(self, c):
        low, high = andor.GetEMGainRange()
        error_code = andor.error['GetEmGainRange']
        return error_code, low, high

    @setting(26, returns='iiv')
    def get_fastest_recommended_vs_speed(self, c):
        index, speed = andor.GetFastestRecommendedVSSpeed()
        error_code = andor.error['GetFastestRecommendedVSSpeed']
        return error_code, index, speed

    @setting(27, channel='i', typ='i', index='i', returns='iv')
    def get_hs_speed(self, c, channel, typ, index):
        speed = andor.GetHSSpeed(channel, typ, index)
        error_code = andor.error['GetHSSpeed']
        return error_code, speed

    @setting(28, returns='ii')
    def get_number_ad_channels(self, c):
        channels = andor.GetNumberADChannels()
        error_code = andor.error['GetNumberADChannels']
        return error_code, channels

    @setting(29, channel='i', typ='i', returns='ii')
    def get_number_hs_speeds(self, c, channel, typ):
        speeds = andor.GetNumberHSSpeeds(channel, typ)
        error_code = andor.error['GetNumberHSSpeeds']
        return error_code, speeds

    @setting(30, returns='ii')
    def get_number_pre_amp_gains(self, c):
        noGains = andor.GetNumberPreAmpGains()
        error_code = andor.error['GetNumberPreAmpGains']
        return error_code, noGains

    @setting(31, returns='ii')
    def get_number_vs_speeds(self, c):
        speeds = andor.GetNumberVSSpeeds()
        error_code = andor.error['GetNumberVSSpeeds']
        return error_code, speeds

    @setting(32, index='i', returns='ii')
    def get_pre_amp_gain(self, c, index):
        gain = andor.GetPreAmpGain(index)
        error_code = andor.error['GetPreAmpGain']
        return error_code, gain

    @setting(33, returns='is')
    def get_status(self, c):
        status = andor.GetStatus()
        error_code = andor.error['GetStatus']
        return error_code, status

    @setting(34, returns='ii')
    def get_temperature(self, c):
        temperature = andor.GetTemperature()
        error_code = andor.error['GetTemperature']
        return error_code, temperature

    @setting(35, index='i', returns='iv')
    def get_vs_speed(self, c, index):
        speed = andor.GetVSSpeed(index)
        error_code = andor.error['GetVSSpeed']
        return error_code, speed

    @setting(36, returns='is')
    def initialize(self, c):
        initdir = andor.Initialize()
        error_code = andor.error['Initialize']
        return error_code, initdir

    @setting(37, returns='ii')
    def is_cooler_on(self, c):
        iCoolerStatus = andor.IsCoolerOn()
        error_code = andor.error['IsCoolerOn']
        return error_code, iCoolerStatus

    @setting(38, time='v', returns='i')
    def set_accumulation_cycle_time(self, c, time):
        andor.SetAccumulationCycleTime(time)
        error_code = andor.error['SetAccumulationCycleTime']
        return error_code

    @setting(39, mode='i', returns='i')
    def set_acquisition_mode(self, c, mode):
        andor.SetAcquisitionMode(mode)
        error_code = andor.error['SetAcquisitionMode']
        return error_code

    @setting(40, channel='i', returns='i')
    def set_ad_channel(self, c, channel):
        andor.SetADChannel(channel)
        error_code = andor.error['SetADChannel']
        return error_code

    @setting(41, mode='i', returns='i')
    def set_cooler_mode(self, c, mode):
        andor.SetCoolerMode(mode)
        error_code = andor.error['SetCoolerMode']
        return error_code

    @setting(42, cameraHandle='i', returns='i')
    def set_current_camera(self, c, cameraHandle):
        andor.SetCurrentCamera(cameraHandle)
        error_code = andor.error['SetCurrentCamera']
        return error_code

    @setting(43, gainAdvanced='i', returns='i')
    def set_em_advanced(self, c, gainAdvanced):
        andor.SetEMAdvanced(gainAdvanced)
        error_code = andor.error['SetEMAdvanced']
        return error_code

    @setting(44, gain='i', returns='i')
    def set_emccd_gain(self, c, gain):
        andor.SetEMCCDGain(gain)
        error_code = andor.error['SetEMCCDGain']
        return error_code

    @setting(45, mode='i', returns='i')
    def set_em_gain_mode(self, c, mode):
        andor.SetEMGainMode(mode)
        error_code = andor.error['SetEMGainMode']
        return error_code

    @setting(46, time='v', returns='i')
    def set_exposure_time(self, c, time):
        andor.SetExposureTime(time)
        error_code = andor.error['SetExposureTime']
        return error_code

    @setting(47, mode='i', returns='i')
    def set_fan_mode(self, c, mode):
        andor.SetFanMode(mode)
        error_code = andor.error['SetFanMode']
        return error_code
    
    @setting(48, exposedRows='i', seriesLength='i', time='v', 
             mode='i', hbin='i', vbin='i', returns='i')
    def set_fast_kinetics(self, c, exposedRows, seriesLength, time,
                             mode, hbin, vbin):
        andor.SetFastKinetics(exposedRows, seriesLength, time, mode, hbin, vbin)
        error_code = andor.error['SetFastKinetics']
        return error_code

    @setting(49, exposedRows='i', seriesLength='i', time='v', 
             mode='i', hbin='i', vbin='i', offset='i', returns='i')
    def set_fast_kinetics_ex(self, c, exposedRows, seriesLength, time,
                             mode, hbin, vbin, offset):
        andor.SetFastKineticsEx(exposedRows, seriesLength, time, mode, hbin, vbin,
                              offset)
        error_code = andor.error['SetFastKineticsEx']
        return error_code

    @setting(50, mode='i', returns='i')
    def set_frame_transfer_mode(self, c, mode):
        andor.SetFrameTransferMode(mode)
        error_code = andor.error['SetFrameTransferMode']
        return error_code

    @setting(51, typ='i', index='i', returns='i')
    def set_hs_speed(self, c, typ, index):
        andor.SetHSSpeed(typ, index)
        error_code = andor.error['SetHSSpeed']
        return error_code

    @setting(52, hbin='i', vbin='i', hstart='i', hend='i', 
             vstart='i', vend='i', returns='i')
    def set_image(self, c, hbin, vbin, hstart, hend, vstart, vend):
        andor.SetImage(hbin, vbin, hstart, hend, vstart, vend)
        error_code = andor.error['SetImage']
        return error_code

    @setting(53, iHFlip='i', iVFlip='i', returns='i')
    def set_image_flip(self, c, iHFlip, iVFlip):
        andor.SetImageFlip(iHFlip, iVFlip)
        error_code = andor.error['SetImageFlip']
        return error_code

    @setting(54, iRotate='i', returns='i')
    def set_image_rotate(self, c, iRotate):
        andor.SetImageRotate(iRotate)
        error_code = andor.error['SetImageRotate']
        return error_code

    @setting(55, time='v', returns='i')
    def set_kinetic_cycle_time(self, c, time):
        andor.SetKineticCycleTime(time)
        error_code = andor.error['SetKineticCycleTime']
        return error_code

    @setting(56, number='i', returns='i')
    def set_number_accumulations(self, c, number):
        andor.SetNumberAccumulations(number)
        error_code = andor.error['SetNumberAccumulations']
        return error_code

    @setting(57, number='i', returns='i')
    def set_number_kinetics(self, c, number):
        andor.SetNumberKinetics(number)
        error_code = andor.error['SetNumberKinetics']
        return error_code

    @setting(58, index='i', returns='i')
    def set_output_amplifier(self, c, index):
        andor.SetOutputAmplifier(index)
        error_code = andor.error['SetOutputAmplifier']
        return error_code

    @setting(59, index='i', returns='i')
    def set_pre_amp_gain(self, c, index):
        andor.SetPreAmpGain(index)
        error_code = andor.error['SetPreAmpGain']
        return error_code

    @setting(60, mode='i', returns='i')
    def set_read_mode(self, c, mode):
        andor.SetReadMode(mode)
        error_code = andor.error['SetReadMode']
        return error_code

    @setting(61, typ='i', mode='i', closingtime='i', 
             openingtime='i', returns='i')
    def set_shutter(self, c, typ, mode, closingtime, openingtime):
        andor.SetShutter(typ, mode, closingtime, openingtime)
        error_code = andor.error['SetShutter']
        return error_code

    @setting(62, typ='i', mode='i', closingtime='i', 
             openingtime='i', extmode='i')
    def set_shutter_ex(self, c, typ, mode, closingtime, openingtime, 
                       extmode):
        andor.SetShutterEx(typ, mode, closingtime, openingtime, extmode)
        error_code = andor.error['SetShutterEx']
        return error_code

    @setting(63, temperature='i', returns='i')
    def set_temperature(self, c, temperature):
        andor.SetTemperature(temperature)
        error_code = andor.error['SetTemperature']
        return error_code

    @setting(64, mode='i', returns='i')
    def set_trigger_mode(self, c, mode):
        andor.SetTriggerMode(mode)
        error_code = andor.error['SetTriggerMode']
        return error_code

    @setting(65, index='i', returns='i')
    def set_vs_speed(self, c, index):
        andor.SetVSSpeed(index)
        error_code = andor.error['SetVSSpeed']
        return error_code

    @setting(66, returns='i')
    def shut_down(self, c):
        andor.ShutDown()
        error_code = andor.error['ShutDown']
        return error_code

    @setting(67, returns='i')
    def start_acquisition(self, c):
        andor.StartAcquisition()
        error_code = andor.error['StartAcquisition']
        return error_code

    @setting(68, returns='i')
    def wait_for_acquisition(self, c):
        andor.WaitForAcquisition()
        error_code = andor.error['WaitForAcquisition']
        return error_code

    @setting(69, returns='i')
    def set_single_track(self, c, center, height):
        andor.SetSingleTrack(center, height)
        error_code = andor.error['SetSingleTrack']
        return error_code

    @setting(70, returns='i')
    def set_baseline_clamp(self, c, state):
        andor.SetBaselineClamp(state)
        error_code = andor.error['SetBaselineClamp']
        return error_code

    @setting(71, returns='i')
    def wait_for_acquisition_timeout(self, c, iTimeOutMs):
        andor.WaitForAcquisitionTimeOut(iTimeOutMs)
        error_code = andor.error['WaitForAcquisitionTimeOut']
        return error_code

Server = AndorServer

if __name__ == "__main__":
    from labrad import util
    util.runServer(Server())
