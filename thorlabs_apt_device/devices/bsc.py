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

__all__ = ["BSC201", "BSC201_DRV250"]

from .. import protocol as apt
from .aptdevice_motor import APTDevice_BayUnit
from ..enums import EndPoint


class BSC201(APTDevice_BayUnit):
    """
    A class for ThorLabs APT device model BSC201.

    It is based off :class:`BBD_BSC` configured with a single channel and the BSC the serial number
    preset in the initialisation method.

    Note that it seems the BSC201 will send automatic status updates, but does not accept the 
    corresponding acknowledgement message, and so will stop responding after ~5 seconds if they are
    enabled. As a workaround, the status of the device will be polled.

    Additionally, it seems that the initial movement and homing velocities can be effectively zero,
    making it seem like the device is not working, though it is actually just moving extremely
    slowly.
    It's a good idea to ensure sensible values are set for :meth:`set_velocity_params`, :meth:`set_jog_params`
    and :meth:`set_home_params` during initialisation.

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

        super().__init__(serial_port=serial_port, vid=vid, pid=pid, manufacturer=manufacturer, product=product, serial_number=serial_number, location=location, x=1, home=home, invert_direction_logic=invert_direction_logic, swap_limit_switches=swap_limit_switches, status_updates="polled")


class BSC201_DRV250(BSC201):
    """
    A class for ThorLabs APT device model BSC201 with DRV250 stepper-motor-driven actuator, sold as
    a package as the `LNR502 and LNR502E <https://www.thorlabs.com/newgrouppage9.cfm?objectgroup_id=2297&pn=LNR502E/M>`__.

    It is based off :class:`BSC201`, but with sensible default movement parameters configured for the actuator.

    For the DRV250, there are 409600 microsteps/mm, 21987328 microsteps/mm/s, and 4506 microsteps/mm/s/s.

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

        super().__init__(serial_port=serial_port, vid=vid, pid=pid, manufacturer=manufacturer, product=product, serial_number=serial_number, location=location, home=home, invert_direction_logic=invert_direction_logic, swap_limit_switches=swap_limit_switches)

        # Initial velocity parameters are effectively zero on startup, set something more sensible
        # Homing is initiated 1.0s after init, so hopefully these will take effect before then...
        for bay_i, _ in enumerate(self.bays):
            for channel_i, _ in enumerate(self.channels):
                self.set_velocity_params(acceleration=4506, max_velocity=21987328, bay=bay_i, channel=channel_i)
                self.set_jog_params(size=409600, acceleration=4506, max_velocity=21987328, bay=bay_i, channel=channel_i)
                self.set_home_params(velocity=21987328, offset_distance=20480, bay=bay_i, channel=channel_i)
       
