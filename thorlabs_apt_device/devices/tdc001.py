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

__all__ = ["TDC001"]

import thorlabs_apt_protocol as apt

from .aptdevice_dc import APTDevice_DC
from ..enums import EndPoint

class TDC001(APTDevice_DC):
    """
    A class specific to a particular ThorLabs APT device model.

    It is based off :class:`APTDevice_DC` with some customisation for the specifics of the device.
    For example, the controller is single bay/channel, has inverted direction logic, and has a
    few extra device-specific commands.

    Additionally, as it is a single bay/channel controller, aliases of ``status = status_[0][0]``
    etc are created for convenience.

    :param serial_port: Serial port device the device is connected to.
    :param serial_number: Regular expression matching the serial number of device to search for.
    :param home: Perform a homing operation on initialisation.
    :param invert_direction_logic: Invert the meaning of "forward" and "reverse".
    """
    def __init__(self, serial_port=None, serial_number="83", home=True, invert_direction_logic=True):
        super().__init__(serial_port=serial_port, serial_number=serial_number, home=home, invert_direction_logic=invert_direction_logic, controller=EndPoint.RACK, bays=(EndPoint.BAY0,), channels=(1,))
        
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
        
        self.pidparams = {
            "proportional" : 0,
            "integral" : 0,
            "differential" : 0,
            "integral_limits" : 0,
            "filter_control" : 0,
            # Update message fields
            "msg" : "",
            "msgid" : 0,
            "source" : 0,
            "dest" : 0,
            "chan_ident" : 0,
        }
        """
        Array of dictionaries of PID algorithm parameters.

        As a device may have multiple card bays, each with multiple channels, this data structure
        is an array of array of dicts. The first axis of the array indexes the bay, the second
        indexes the channel.
        
        Keys are ``"proportional"``, ``"integral"``, ``"differential"``, ``"integral_limits"``, and
        ``"filter_control"``.
        """
        # Request current PID parameters
        self._loop.call_soon_threadsafe(self._write, apt.mot_req_dcpidparams(source=EndPoint.HOST, dest=self.bays[0], chan_ident=self.channels[0]))

    def _process_message(self, m):
        super()._process_message(m)
        if m.msg == "mot_get_dcpidparams":
            self.pidparams.update(m._asdict())
