# Copyright 2021 Patrick C. Tapping
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program.  If not, see <http://www.gnu.org/licenses/>.

__all__ = ["BBD_BSC", "BBD201", "BSC201"]

from .. import protocol as apt
from .aptdevice_motor import APTDevice_Motor_Trigger
from ..enums import EndPoint

class BBD_BSC(APTDevice_Motor_Trigger):
    """
    A class for ThorLabs APT device models BBD10x, BBD20x, BSC10x, BSC20x, where x is the number of channels (1, 2 or 3).

    It is based off :class:`APTDevice_Motor_Trigger` with some customisation for the specifics of the device.

    Note that the BBD and BSCs are referred to as a x-channel controllers, but the actual device layout is that 
    the controller is a "rack" system with three bays, where x number of single-channel
    controller cards may be installed. In other words, the BBD203 "3 channel" controller actually
    has 3 populated bays (``bays=(EndPoint.BAY0, EndPoint.BAY1, EndPoint.BAY2)``), each of which
    only controls a single channel (``channels=(1,)``).

    The parameter ``x`` configures the number of channels.
    If ``x=1`` it is a single bay/channel controller, and aliases of ``status = status_[0][0]``
    etc are created for convenience.

    :param x: Number of channels the device controls.
    :param serial_port: Serial port device the device is connected to.
    :param vid: Numerical USB vendor ID to match.
    :param pid: Numerical USB product ID to match.
    :param manufacturer: Regular expression to match to a device manufacturer string.
    :param product: Regular expression to match to a device product string.
    :param serial_number: Regular expression to match to a device serial number.
    :param home: Perform a homing operation on initialisation.
    :param invert_direction_logic: Invert the meaning of "forward" and "reverse" directions.
    :param swap_limit_switches: Swap "forward" and "reverse" limit switch values.
    """
    def __init__(self, serial_port=None, vid=None, pid=None, manufacturer=None, product=None, serial_number=None, location=None, x=1, home=True, invert_direction_logic=False, swap_limit_switches=True):
        
        # Configure number of bays
        if x == 3:
            bays = (EndPoint.BAY0, EndPoint.BAY1, EndPoint.BAY2)
        elif x == 2:
            bays = (EndPoint.BAY0, EndPoint.BAY1)
        else:
            bays = (EndPoint.BAY0,)

        super().__init__(serial_port=serial_port, vid=vid, pid=pid, manufacturer=manufacturer, product=product, serial_number=serial_number, location=location, home=home, invert_direction_logic=invert_direction_logic, swap_limit_switches=swap_limit_switches, controller=EndPoint.RACK, bays=bays, channels=(1,))

        if x == 1:
            self.status = self.status_[0][0]
            """Alias to first bay/channel of :data:`~thorlabs_apt_device.devices.aptdevice_dc.APTDevice_Motor.status_`."""
            
            self.velparams = self.velparams_[0][0]
            """Alias to first bay/channel of :data:`~thorlabs_apt_device.devices.aptdevice_dc.APTDevice_Motor.velparams_`"""
            
            self.genmoveparams = self.genmoveparams_[0][0]
            """Alias to first bay/channel of :data:`~thorlabs_apt_device.devices.aptdevice_dc.APTDevice_Motor.genmoveparams_`"""
            
            self.jogparams = self.jogparams_[0][0]
            """Alias to first bay/channel of :data:`~thorlabs_apt_device.devices.aptdevice_dc.APTDevice_Motor.jogparams_`"""
            
            self.trigger = self.trigger_[0][0]
            """Alias to first bay/channel of :data:`~BBD.trigger_`"""


class BBD201(BBD_BSC):
    """
    A class for ThorLabs APT device model BBD201.

    It is based off :class:`BBD_BSC` configured with a single channel and the the BBD serial number
    preset in the initialisation method.

    :param serial_port: Serial port device the device is connected to.
    :param vid: Numerical USB vendor ID to match.
    :param pid: Numerical USB product ID to match.
    :param manufacturer: Regular expression to match to a device manufacturer string.
    :param product: Regular expression to match to a device product string.
    :param serial_number: Regular expression to match to a device serial number.
    :param home: Perform a homing operation on initialisation.
    :param invert_direction_logic: Invert the meaning of "forward" and "reverse" directions.
    :param swap_limit_switches: Swap "forward" and "reverse" limit switch values.
    """
    def __init__(self, serial_port=None, vid=None, pid=None, manufacturer=None, product=None, serial_number="73", location=None, home=True, invert_direction_logic=False, swap_limit_switches=True):

        super().__init__(serial_port=serial_port, vid=vid, pid=pid, manufacturer=manufacturer, product=product, serial_number=serial_number, location=location, x=1, home=home, invert_direction_logic=invert_direction_logic, swap_limit_switches=swap_limit_switches)


class BSC201(BBD_BSC):
    """
    A class for ThorLabs APT device model BSC201.

    It is based off :class:`BBD_BSC` configured with a single channel and the BSC the serial number
    preset in the initialisation method.

    :param serial_port: Serial port device the device is connected to.
    :param vid: Numerical USB vendor ID to match.
    :param pid: Numerical USB product ID to match.
    :param manufacturer: Regular expression to match to a device manufacturer string.
    :param product: Regular expression to match to a device product string.
    :param serial_number: Regular expression to match to a device serial number.
    :param home: Perform a homing operation on initialisation.
    :param invert_direction_logic: Invert the meaning of "forward" and "reverse" directions.
    :param swap_limit_switches: Swap "forward" and "reverse" limit switch values.
    """
    def __init__(self, serial_port=None, vid=None, pid=None, manufacturer=None, product=None, serial_number="40", location=None, home=True, invert_direction_logic=False, swap_limit_switches=True):

        super().__init__(serial_port=serial_port, vid=vid, pid=pid, manufacturer=manufacturer, product=product, serial_number=serial_number, location=location, x=1, home=home, invert_direction_logic=invert_direction_logic, swap_limit_switches=swap_limit_switches)
