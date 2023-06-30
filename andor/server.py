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
from labrad.server import LabradServer, setting

from andor.andor import Andor

class AndorServer(LabradServer):
    """ Provides access to andor camera using pyandor """
    name = '%LABRADNODE%_andor'

    def initServer(self):
        global andor
        andor = Andor()
        andor.Initialize()
        super(AndorServer, self).initServer()
    
    def stopServer(self):
        andor.ShutDown()
        super(AndorServer, self).stopServer()

    def _set_serial(self, serial):
        # in a multi camera system, this could call andor.SetCurrentCamera.
        andor.SetCurrentCamera(serial)

    @setting(10, serial='i', returns='i')
    def abort_acquisition(self, c, serial):
        self._set_serial(serial)
        andor.AbortAcquisition()
        error_code = andor.error['AbortAcquisition']
        return error_code

    @setting(11, serial='i', returns='i')
    def cancel_wait(self, c, serial):
        self._set_serial(serial)
        andor.CancelWait()
        error_code = andor.error['CancelWait']
        return error_code

    @setting(12, serial='i', returns='i')
    def cooler_off(self, c, serial):
        self._set_serial(serial)
        andor.CoolerOFF()
        error_code = andor.error['CoolerOFF']
        return error_code

    @setting(13, serial='i', returns='i')
    def cooler_on(self, c, serial):
        self._set_serial(serial)
        andor.CoolerON()
        error_code = andor.error['CoolerON']
        return error_code

    @setting(14, serial='i', size='i', returns='i*i')
    def get_acquired_data(self, c, serial, size):
        self._set_serial(serial)
        arr = andor.GetAcquiredData(size)
        error_code = andor.error['GetAcquiredData']
        return error_code, arr
    
    @setting(15, serial='i', size='i', returns='i*i')
    def get_acquired_data_16(self, c, serial, size):
        self._set_serial(serial)
        arr = andor.GetAcquiredData16(size)
        error_code = andor.error['GetAcquiredData16']
        return error_code, arr

    @setting(16, serial='i', returns='iii')
    def get_acquisition_progress(self, c, serial):
        self._set_serial(serial)
        acc, series = andor.GetAcquisitionProgress()
        error_code = andor.error['GetAcquisitionProgress']
        return error_code, acc, series

    @setting(17, serial='i', returns='iiii')
    def get_acquisition_timings(self, c, serial):
        self._set_serial(serial)
        exposure, accumulate, kinetic = andor.GetAcquisitionTimings()
        error_code = andor.error['GetAcquisitionTimings']
        return error_code, exposure, accumulate, kinetic

    @setting(18, serial='i', returns='ii')
    def get_available_cameras(self, c, serial):
        self._set_serial(serial)
        totalCameras = andor.GetAvailableCameras()
        error_code = andor.error['GetAvailableCameras']
        return error_code, totalCameras

    @setting(19, serial='i', channel='i', returns='ii')
    def get_bit_depth(self, c, serial, channel):
        self._set_serial(serial)
        depth = andor.GetBitDepth(channel)
        error_code = andor.error['GetBitDepth']
        return error_code, depth

    @setting(20, serial='i', cameraIndex='i', returns='ii')
    def get_camera_handle(self, c, serial, cameraIndex):
        self._set_serial(serial)
        cameraHandle = andor.GetCameraHandle(cameraIndex)
        error_code = andor.error['GetCameraHandle']
        return error_code, cameraHandle

    @setting(21, serial='i', returns='ii')
    def get_camera_serial_number(self, c, serial):
        self._set_serial(serial)
        number = andor.GetCameraSerialNumber()
        error_code = andor.error['GetCameraSerialNumber']
        return error_code, number

    @setting(22, serial='i', returns='ii')
    def get_current_camera(self, c, serial):
        self._set_serial(serial)
        cameraHandle = andor.GetCurrentCamera()
        error_code = andor.error['GetCurrentCamera']
        return error_code, cameraHandle

    @setting(23, serial='i', returns='iii')
    def get_detector(self, c, serial):
        self._set_serial(serial)
        xpixels, ypixels = andor.GetDetector()
        error_code = andor.error['GetDetector']
        return error_code, xpixels, ypixels

    @setting(24, serial='i', returns='ii')
    def get_emccd_gain(self, c, serial):
        self._set_serial(serial)
        gain = andor.GetEMCCDGain()
        error_code = andor.error['GetEMCCDGain']
        return error_code, gain

    @setting(25, serial='i', returns='iii')
    def get_em_gain_range(self, c, serial):
        self._set_serial(serial)
        low, high = andor.GetEMGainRange()
        error_code = andor.error['GetEmGainRange']
        return error_code, low, high

    @setting(26, serial='i', returns='iiv')
    def get_fastest_recommended_vs_speed(self, c, serial):
        self._set_serial(serial)
        index, speed = andor.GetFastestRecommendedVSSpeed()
        error_code = andor.error['GetFastestRecommendedVSSpeed']
        return error_code, index, speed

    @setting(27, serial='i', channel='i', typ='i', index='i', returns='iv')
    def get_hs_speed(self, c, serial, channel, typ, index):
        self._set_serial(serial)
        speed = andor.GetHSSpeed(channel, typ, index)
        error_code = andor.error['GetHSSpeed']
        return error_code, speed

    @setting(28, serial='i', returns='ii')
    def get_number_ad_channels(self, c, serial):
        self.set_serial(serial)
        channels = andor.GetNumberADChannels()
        error_code = andor.error['GetNumberADChannels']
        return error_code, channels

    @setting(29, serial='i', channel='i', typ='i', returns='ii')
    def get_number_hs_speeds(self, c, serial, channel, typ):
        self._set_serial(serial)
        speeds = andor.GetNumberHSSpeeds(channel, typ)
        error_code = andor.error['GetNumberHSSpeeds']
        return error_code, speeds

    @setting(30, serial='i', returns='ii')
    def get_number_pre_amp_gains(self, c, serial):
        self._set_serial(serial)
        noGains = andor.GetNumberPreAmpGains()
        error_code = andor.error['GetNumberPreAmpGains']
        return error_code, noGains

    @setting(31, serial='i', returns='ii')
    def get_number_vs_speeds(self, c, serial):
        self._set_serial(serial)
        speeds = andor.GetNumberVSSpeeds()
        error_code = andor.error['GetNumberVSSpeeds']
        return error_code, speeds

    @setting(32, serial='i', index='i', returns='ii')
    def get_pre_amp_gain(self, c, serial, index):
        self._set_serial(serial)
        gain = andor.GetPreAmpGain(index)
        error_code = andor.error['GetPreAmpGain']
        return error_code, gain

    @setting(33, serial='i', returns='is')
    def get_status(self, c, serial):
        self._set_serial(serial)
        status = andor.GetStatus()
        error_code = andor.error['GetStatus']
        return error_code, status

    @setting(34, serial='i', returns='ii')
    def get_temperature(self, c, serial):
        self._set_serial(serial)
        temperature = andor.GetTemperature()
        error_code = andor.error['GetTemperature']
        return error_code, temperature

    @setting(35, serial='i', index='i', returns='iv')
    def get_vs_speed(self, c, serial, index):
        self._set_serial(serial)
        speed = andor.GetVSSpeed(index)
        error_code = andor.error['GetVSSpeed']
        return error_code, speed

    @setting(36, serial='i', returns='is')
    def initialize(self, c, serial):
        self._set_serial(serial)
        initdir = andor.Initialize()
        error_code = andor.error['Initialize']
        return error_code, initdir

    @setting(37, serial='i', returns='ii')
    def is_cooler_on(self, c, serial):
        self._set_serial(serial)
        iCoolerStatus = andor.IsCoolerOn()
        error_code = andor.error['IsCoolerOn']
        return error_code, iCoolerStatus

    @setting(38, serial='i', time='v', returns='i')
    def set_accumulation_cycle_time(self, c, serial, time):
        self._set_serial(serial)
        andor.SetAccumulationCycleTime(time)
        error_code = andor.error['SetAccumulationCycleTime']
        return error_code

    @setting(39, serial='i', mode='i', returns='i')
    def set_acquisition_mode(self, c, serial, mode):
        self._set_serial(serial)
        andor.SetAcquisitionMode(mode)
        error_code = andor.error['SetAcquisitionMode']
        return error_code

    @setting(40, serial='i', channel='i', returns='i')
    def set_ad_channel(self, c, serial, channel):
        self._set_serial(serial)
        andor.SetADChannel(channel)
        error_code = andor.error['SetADChannel']
        return error_code

    @setting(41, serial='i', mode='i', returns='i')
    def set_cooler_mode(self, c, serial, mode):
        self._set_serial(serial)
        andor.SetCoolerMode(mode)
        error_code = andor.error['SetCoolerMode']
        return error_code

    @setting(42, serial='i', cameraHandle='i', returns='i')
    def set_current_camera(self, c, serial, cameraHandle):
        self._set_serial(serial)
        andor.SetCurrentCamera(cameraHandle)
        error_code = andor.error['SetCurrentCamera']
        return error_code

    @setting(43, serial='i', gainAdvanced='i', returns='i')
    def set_em_advanced(self, c, serial, gainAdvanced):
        self._set_serial(serial)
        andor.SetEMAdvanced(gainAdvanced)
        error_code = andor.error['SetEMAdvanced']
        return error_code

    @setting(44, serial='i', gain='i', returns='i')
    def set_emccd_gain(self, c, serial, gain):
        self._set_serial(serial)
        andor.SetEMCCDGain(gain)
        error_code = andor.error['SetEMCCDGain']
        return error_code

    @setting(45, serial='i', mode='i', returns='i')
    def set_em_gain_mode(self, c, serial, mode):
        self._set_serial(serial)
        andor.SetEMGainMode(mode)
        error_code = andor.error['SetEMGainMode']
        return error_code

    @setting(46, serial='i', time='v', returns='i')
    def set_exposure_time(self, c, serial, time):
        self._set_serial(serial)
        andor.SetExposureTime(time)
        error_code = andor.error['SetExposureTime']
        return error_code

    @setting(47, serial='i', mode='i', returns='i')
    def set_fan_mode(self, c, serial, mode):
        self._set_serial(serial)
        andor.SetFanMode(mode)
        error_code = andor.error['SetFanMode']
        return error_code
    
    @setting(48, serial='i', exposedRows='i', seriesLength='i', time='v', 
             mode='i', hbin='i', vbin='i', returns='i')
    def set_fast_kinetics(self, c, serial, exposedRows, seriesLength, time,
                             mode, hbin, vbin):
        self._set_serial(serial)
        andor.SetFastKinetics(exposedRows, seriesLength, time, mode, hbin, vbin)
        error_code = andor.error['SetFastKinetics']
        return error_code

    @setting(49, serial='i', exposedRows='i', seriesLength='i', time='v', 
             mode='i', hbin='i', vbin='i', offset='i', returns='i')
    def set_fast_kinetics_ex(self, c, serial, exposedRows, seriesLength, time,
                             mode, hbin, vbin, offset):
        self._set_serial(serial)
        andor.SetFastKineticsEx(exposedRows, seriesLength, time, mode, hbin, vbin,
                              offset)
        error_code = andor.error['SetFastKineticsEx']
        return error_code

    @setting(50, serial='i', mode='i', returns='i')
    def set_frame_transfer_mode(self, c, serial, mode):
        self._set_serial(serial)
        andor.SetFrameTransferMode(mode)
        error_code = andor.error['SetFrameTransferMode']
        return error_code

    @setting(51, serial='i', typ='i', index='i', returns='i')
    def set_hs_speed(self, c, serial, typ, index):
        self._set_serial(serial)
        andor.SetHSSpeed(typ, index)
        error_code = andor.error['SetHSSpeed']
        return error_code

    @setting(52, serial='i', hbin='i', vbin='i', hstart='i', hend='i', 
             vstart='i', vend='i', returns='i')
    def set_image(self, c, serial, hbin, vbin, hstart, hend, vstart, vend):
        self._set_serial(serial)
        andor.SetImage(hbin, vbin, hstart, hend, vstart, vend)
        error_code = andor.error['SetImage']
        return error_code

    @setting(53, serial='i', iHFlip='i', iVFlip='i', returns='i')
    def set_image_flip(self, c, serial, iHFlip, iVFlip):
        self._set_serial(serial)
        andor.SetImageFlip(iHFlip, iVFlip)
        error_code = andor.error['SetImageFlip']
        return error_code

    @setting(54, serial='i', iRotate='i', returns='i')
    def set_image_rotate(self, c, serial, iRotate):
        self._set_serial(serial)
        andor.SetImageRotate(iRotate)
        error_code = andor.error['SetImageRotate']
        return error_code

    @setting(55, serial='i', time='v', returns='i')
    def set_kinetic_cycle_time(self, c, serial, time):
        self._set_serial(serial)
        andor.SetKineticCycleTime(time)
        error_code = andor.error['SetKineticCycleTime']
        return error_code

    @setting(56, serial='i', number='i', returns='i')
    def set_number_accumulations(self, c, serial, number):
        self._set_serial(serial)
        andor.SetNumberAccumulations(number)
        error_code = andor.error['SetNumberAccumulations']
        return error_code

    @setting(57, serial='i', number='i', returns='i')
    def set_number_kinetics(self, c, serial, number):
        self._set_serial(serial)
        andor.SetNumberKinetics(number)
        error_code = andor.error['SetNumberKinetics']
        return error_code

    @setting(58, serial='i', index='i', returns='i')
    def set_output_amplifier(self, c, serial, index):
        self._set_serial(serial)
        andor.SetOutputAmplifier(index)
        error_code = andor.error['SetOutputAmplifier']
        return error_code

    @setting(59, serial='i', index='i', returns='i')
    def set_pre_amp_gain(self, c, serial, index):
        self._set_serial(serial)
        andor.SetPreAmpGain(index)
        error_code = andor.error['SetPreAmpGain']
        return error_code

    @setting(60, serial='i', mode='i', returns='i')
    def set_read_mode(self, c, serial, mode):
        self._set_serial(serial)
        andor.SetReadMode(mode)
        error_code = andor.error['SetReadMode']
        return error_code

    @setting(61, serial='i', typ='i', mode='i', closingtime='i', 
             openingtime='i', returns='i')
    def set_shutter(self, c, serial, typ, mode, closingtime, openingtime):
        self._set_serial(serial)
        andor.SetShutter(typ, mode, closingtime, openingtime)
        error_code = andor.error['SetShutter']
        return error_code

    @setting(62, serial='i', typ='i', mode='i', closingtime='i', 
             openingtime='i', extmode='i')
    def set_shutter_ex(self, c, serial, typ, mode, closingtime, openingtime, 
                       extmode):
        self._set_serial(serial)
        andor.SetShutterEx(typ, mode, closingtime, openingtime, extmode)
        error_code = andor.error['SetShutterEx']
        return error_code

    @setting(63, serial='i', temperature='i', returns='i')
    def set_temperature(self, c, serial, temperature):
        self._set_serial(serial)
        andor.SetTemperature(temperature)
        error_code = andor.error['SetTemperature']
        return error_code

    @setting(64, serial='i', mode='i', returns='i')
    def set_trigger_mode(self, c, serial, mode):
        self._set_serial(serial)
        andor.SetTriggerMode(mode)
        error_code = andor.error['SetTriggerMode']
        return error_code

    @setting(65, serial='i', index='i', returns='i')
    def set_vs_speed(self, c, serial, index):
        self._set_serial(serial)
        andor.SetVSSpeed(index)
        error_code = andor.error['SetVSSpeed']
        return error_code

    @setting(66, serial='i', returns='i')
    def shut_down(self, c, serial):
        self._set_serial(serial)
        andor.ShutDown()
        error_code = andor.error['ShutDown']
        return error_code

    @setting(67, serial='i', returns='i')
    def start_acquisition(self, c, serial):
        self._set_serial(serial)
        andor.StartAcquisition()
        error_code = andor.error['StartAcquisition']
        return error_code

    @setting(68, serial='i', returns='i')
    def wait_for_acquisition(self, c, serial):
        self._set_serial(serial)
        andor.WaitForAcquisition()
        error_code = andor.error['WaitForAcquisition']
        return error_code

    @setting(69, serial='i', returns='i')
    def set_single_track(self, c, serial, center, height):
        self._set_serial(serial)
        andor.SetSingleTrack(center, height)
        error_code = andor.error['SetSingleTrack']
        return error_code

    @setting(70, serial='i', returns='i')
    def set_baseline_clamp(self, c, serial, state):
        self._set_serial(serial)
        andor.SetBaselineClamp(state)
        error_code = andor.error['SetBaselineClamp']
        return error_code

    @setting(71, serial='i', returns='i')
    def wait_for_acquisition_timeout(self, c, serial, iTimeOutMs):
        self._set_serial(serial)
        andor.WaitForAcquisitionTimeOut(iTimeOutMs)
        error_code = andor.error['WaitForAcquisitionTimeOut']
        return error_code

Server = AndorServer

if __name__ == "__main__":
    from labrad import util
    util.runServer(Server())
