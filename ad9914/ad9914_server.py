"""
Interface for talking to AD9914.

..
    ### BEGIN NODE INFO
    [info]
    name = ad9914
    version = 1.1
    description = 
    instancename = %LABRADNODE%_ad9914

    [startup]
    cmdline = %PYTHON32% %FILE%
    timeout = 20

    [shutdown]
    message = 987654321
    timeout = 20
    ### END NODE INFO
"""
import sys

sys.path.append("..")
from server_tools.hardware_interface_server import HardwareInterfaceServer
from labrad.server import setting
from twisted.internet.defer import inlineCallbacks
from ctypes import *

windll.LoadLibrary("adiddseval.dll")
dll = windll.adiddseval


class AD9914Server(HardwareInterfaceServer):
    """
    Server for communicating with AD9914 DDS.

    The current hardware setup uses the microcontroller on the AD9914 evaluation board to control the DDS.
    """

    name = "%LABRADNODE%_ad9914"

    def refresh_available_interfaces(self):
        vid_array = c_int * 1
        pid_array = c_int * 1
        vid = vid_array(0x0456)
        pid = pid_array(0xEE1F)
        length = c_int(1)
        hard_instances = dll.FindHardware(byref(vid), byref(pid), length)
        self.interfaces = {}
        if hard_instances == 0:
            return
        handle_array = c_int * hard_instances

    @inlineCallbacks
    @setting(10, "Set frequency", f="v", ramp="b", ext_trigger="b")
    def set_frequency(self, c, f, ramp=False):
        """
        Set the tone of the DDS.

        Args:
            f (float): frequency in Hz
            ramp (bool): whether to ramp to the new frequency. Default is False.
        """
        yield None

    @inlineCallbacks
    @setting(11, "Force trigger")
    def force_trigger(self, c):
        """
        Trigger the next frequency change.
        """
        yield None


if __name__ == "__main__":
    from labrad import util

    util.runServer(AD9914Server())
