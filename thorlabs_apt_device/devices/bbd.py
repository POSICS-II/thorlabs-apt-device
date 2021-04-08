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

__all__ = ["BBD"]

import thorlabs_apt_protocol as apt

from .aptdevice_dc import APTDevice_DC
from ..enums import EndPoint

class BBD(APTDevice_DC):
    """
    A class for ThorLabs APT device models BBD10x and BBD20x, where x is the number of channels (1, 2 or 3).

    It is based off :class:`APTDevice_DC` with some customisation for the specifics of the device.

    Note that the BBDs are referred to as a x-channel controller, but the actual device layout is that 
    the controller is a "rack" system with three bays, where x number of single-channel
    controller cards may be installed. In other words, the BBD203 "3 channel" controller actually
    has 3 populated bays (``bays=(EndPoint.BAY0, EndPoint.BAY1, EndPoint.BAY2)``), each of which
    only controls a single channel (``channels=(1,)``).

    The parameter ``x`` configures the number of channels.
    If ``x=1`` it is a single bay/channel controller, and aliases of ``status = status_[0][0]``
    etc are created for convenience.

    :param x: Number of channels the device controls.
    :param serial_port: Serial port device the device is connected to.
    :param serial_number: Regular expression matching the serial number of device to search for.
    :param home: Perform a homing operation on initialisation.
    :param invert_direction_logic: Invert the meaning of "forward" and "reverse".
    """
    def __init__(self, serial_port=None, serial_number="73", x=1, home=True, invert_direction_logic=False):
        
        # Configure number of bays
        if x == 3:
            bays = (EndPoint.BAY0, EndPoint.BAY1, EndPoint.BAY2)
        elif x == 2:
            bays = (EndPoint.BAY0, EndPoint.BAY1)
        else:
            bays = (EndPoint.BAY0,)

        super().__init__(serial_port=serial_port, serial_number=serial_number, home=home, invert_direction_logic=invert_direction_logic, controller=EndPoint.RACK, bays=bays, channels=(1,))
        
        if x == 1:
            self.status = self.status_[0][0]
            """Alias to first bay/channel of :data:`APTDevice_DC.status_`."""
            
            self.velparams = self.velparams_[0][0]
            """Alias to first bay/channel of :data:`APTDevice_DC.velparams_`"""
            
            self.genmoveparams = self.genmoveparams_[0][0]
            """Alias to first bay/channel of :data:`APTDevice_DC.genmoveparams_`"""
            
            self.jogparams = self.jogparams_[0][0]
            """Alias to first bay/channel of :data:`APTDevice_DC.jogparams_`"""
            
            self.ledmodes = self.ledmodes_[0][0]
            """Alias to first bay/channel of :data:`APTDevice_DC.ledmodes_`"""