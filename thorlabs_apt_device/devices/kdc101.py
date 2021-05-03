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

__all__ = ["KDC101"]

from .. import protocol as apt
from . tdc001 import TDC001

class KDC101(TDC001):
    """
    A class specific to the ThorLabs KDC101 motion controller.

    It can be considered an updated version of the
    :mod:`TDC001 <thorlabs_apt_device.devices.tdc001>`, with the addition of some features like
    external triggering modes.

    As it is a single bay/channel controller, aliases of ``status = status_[0][0]``
    etc are created for convenience.

    :param serial_port: Serial port device the device is connected to.
    :param serial_number: Regular expression matching the serial number of device to search for.
    :param home: Perform a homing operation on initialisation.
    :param invert_direction_logic: Invert the meaning of "forward" and "reverse".
    :param swap_limit_switches: Swap the "forward" and "reverse" limit switch signals.
    """
    def __init__(self, serial_port=None, serial_number=None, home=True, invert_direction_logic=True, swap_limit_switches=True):
        super().__init__(serial_port=serial_port, serial_number=serial_number, home=home, invert_direction_logic=invert_direction_logic, swap_limit_switches=swap_limit_switches)
        

    def _process_message(self, m):
        super()._process_message(m)
        print(m)

