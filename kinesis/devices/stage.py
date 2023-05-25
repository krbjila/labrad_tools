import os, sys
from twisted.internet.defer import inlineCallbacks, returnValue

sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), '../..'))
from server_tools.device_server import DeviceWrapper

import clr
clr.AddReference("C:\\Program Files\\Thorlabs\\Kinesis\\Thorlabs.MotionControl.DeviceManagerCLI.dll.")
clr.AddReference("C:\\Program Files\\Thorlabs\\Kinesis\\Thorlabs.MotionControl.GenericMotorCLI.dll.")
clr.AddReference("C:\\Program Files\\Thorlabs\\Kinesis\\Thorlabs.MotionControl.KCube.BrushlessMotorCLI.dll.")

from Thorlabs.MotionControl.DeviceManagerCLI import *
from Thorlabs.MotionControl.GenericMotorCLI import *
from Thorlabs.MotionControl.GenericMotorCLI.Settings import KCubeTriggerConfigSettings
from Thorlabs.MotionControl.KCube.BrushlessMotorCLI import *
from System import Decimal

class Stage(DeviceWrapper):
    def __init__(self, config):

        for key, value in config.items():
            setattr(self, key, value)

        self.address = self.serial
        super(Stage, self).__init__({})
    
    @inlineCallbacks
    def initialize(self):
        yield DeviceManagerCLI.BuildDeviceList()
        self.stage = yield KCubeBrushlessMotor.CreateKCubeBrushlessMotor(self.serial)
        yield self.stage.Connect(self.serial)
        yield self.stage.StartPolling(50)

        if not self.stage.IsSettingsInitialized():
            yield self.stage.WaitForSettingsInitialized(10000)  # 10 second timeout
            assert self.stage.IsSettingsInitialized() is True

        # Before homing or moving device, ensure the motors configuration is loaded
        m_config = yield self.stage.LoadMotorConfiguration(self.serial, DeviceConfiguration.DeviceSettingsUseOptionType.UseDeviceSettings)

    @inlineCallbacks
    def enable(self):
        yield self.stage.EnableDevice()

    @inlineCallbacks
    def disable(self):
        yield self.stage.DisableDevice()
    
    @inlineCallbacks
    def home(self, timeout=10.0):
        """
        home(self, timeout=10)

        Homes the stage.

        Args:
            timeout (float, optional): The timeout in seconds. Defaults to 10.
        """
        yield self.stage.Home(round(timeout*1E3))

    @inlineCallbacks
    def move_to(self, position, timeout=10.0):
        yield self.stage.MoveTo(Decimal(position), round(timeout*1E3))
    
    @inlineCallbacks
    def move_by(self, displacement, timeout=10.0):
        yield self.stage.MoveBy(Decimal(displacement), round(timeout*1E3))
    
    @inlineCallbacks
    def get_position(self):
        position = yield self.stage.get_DevicePosition()
        returnValue(float(str(position)))

    @inlineCallbacks
    def move_on_trigger(self, position):
        trigger_config_params = yield self.stage.GetTriggerConfigParams()
        trigger_config_params.Trigger1Mode = KCubeTriggerConfigSettings.TriggerPortMode.TrigIN_AbsoluteMove
        trigger_config_params.Trigger1Polarity = KCubeTriggerConfigSettings.TriggerPolarity.TriggerHigh
        yield self.stage.SetTriggerConfigParams(trigger_config_params)

        yield self.stage.SetMoveAbsolutePosition(Decimal(position))
