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

from .. import protocol as apt
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
    :param invert_direction_logic: Invert the meaning of "forward" and "reverse" directions.
    :param swap_limit_switches: Swap "forward" and "reverse" limit switch values.
    """
    def __init__(self, serial_port=None, serial_number="73", x=1, home=True, invert_direction_logic=False, swap_limit_switches=True):
        
        # Configure number of bays
        if x == 3:
            bays = (EndPoint.BAY0, EndPoint.BAY1, EndPoint.BAY2)
        elif x == 2:
            bays = (EndPoint.BAY0, EndPoint.BAY1)
        else:
            bays = (EndPoint.BAY0,)

        super().__init__(serial_port=serial_port, serial_number=serial_number, home=home, invert_direction_logic=invert_direction_logic, swap_limit_switches=swap_limit_switches, controller=EndPoint.RACK, bays=bays, channels=(1,))
        
        self.trigger_ = [[{
            # Actual integer code returned by device
            "mode" : 0,
            # Unpacked meaning of mode bits
            "input_edge" : "",
            "input_mode" : "",
            "output_logic" : "",
            "output_mode" : "",
            # Update message fields
            "msg" : "",
            "msgid" : 0,
            "source" : 0,
            "dest" : 0,
            "chan_ident" : 0,
        } for _ in self.channels] for _ in self.bays]
        """
        Input and output triggering configuration.

        Fields are ``"input_edge"``, ``"input_mode"``, ``"output_logic"``, and ``"output_mode"``.
        Additionally, ``"mode"`` stores the raw bit field data from the device as an integer.
        """
        # Request current trigger modes
        for bay in self.bays:
            for channel in self.channels:
                self._loop.call_soon_threadsafe(self._write, apt.mot_req_trigger(source=EndPoint.HOST, dest=bay, chan_ident=channel))

        if x == 1:
            self.status = self.status_[0][0]
            """Alias to first bay/channel of :data:`APTDevice_DC.status_`."""
            
            self.velparams = self.velparams_[0][0]
            """Alias to first bay/channel of :data:`APTDevice_DC.velparams_`"""
            
            self.genmoveparams = self.genmoveparams_[0][0]
            """Alias to first bay/channel of :data:`APTDevice_DC.genmoveparams_`"""
            
            self.jogparams = self.jogparams_[0][0]
            """Alias to first bay/channel of :data:`APTDevice_DC.jogparams_`"""
            
            self.trigger = self.trigger_[0][0]
            """Alias to first bay/channel of :data:`BBD.trigger_`"""


    def _process_message(self, m):
        super()._process_message(m)
       
        # Decode bay and channel IDs and check if they match one of ours
        if m.msg in ("mot_get_trigger",):
            # Check if source matches one of our bays
            try:
                bay_i = self.bays.index(m.source)
            except ValueError:
                # Ignore message from unknown bay id
                self._log.warn(f"Message {m.msg} has unrecognised source={m.source}.")
                return
            # Check if channel matches one of our channels
            try:
                channel_i = self.channels.index(m.chan_ident)
            except ValueError:
                    # Ignore message from unknown channel id
                    self._log.warn(f"Message {m.msg} has unrecognised channel={m.chan_ident}.")
                    return
        
        if m.msg == "mot_get_trigger":
            # Trigger mode update message
            self.trigger_[bay_i][channel_i].update(m._asdict())
            # Decode the input bit fields
            self.trigger_[bay_i][channel_i]["input_edge"] = ("falling", "rising")[bool(m.mode & 0b00000001)]
            if m.mode & 0b00000010:
                self.trigger_[bay_i][channel_i]["input_mode"] = "move_relative"
            elif m.mode & 0b00000100:
                self.trigger_[bay_i][channel_i]["input_mode"] = "move_absolute"
            elif m.mode & 0b00001000:
                self.trigger_[bay_i][channel_i]["input_mode"] = "home"
            else:
                self.trigger_[bay_i][channel_i]["input_mode"] = "disabled"
            # Decode the output bit fields
            self.trigger_[bay_i][channel_i]["output_logic"] = ("low", "high")[bool(m.mode & 0b00010000)]
            if m.mode & 0b00100000:
                self.trigger_[bay_i][channel_i]["output_mode"] = "in_motion"
            elif m.mode & 0b01000000:
                self.trigger_[bay_i][channel_i]["output_mode"] = "motion_complete"
            elif m.mode & 0b10000000:
                self.trigger_[bay_i][channel_i]["output_mode"] = "max_velocity"
            else:
                self.trigger_[bay_i][channel_i]["output_mode"] = "disabled"


    def set_trigger(self, input_edge=None, input_mode=None, output_logic=None, output_mode=None, bay=0, channel=0):
        """
        Configure the external input and/or output triggering modes for the device.
        
        The input triggering logic is selected with ``input_edge``:
        
            * ``"rising"`` : Trigger on rising edge (low to high transition).
            * ``"falling"`` : Trigger on falling edge (high to low transition).
    
        On detection of the input trigger, either a relative, absolute, or homing move can be 
        started.
        For the moves, the movement parameters should have been pre-configured using the relevant
        :meth:`move_relative()` or :meth:`move_absolute()` methods, passing the ``now=False``
        parameter to indicate the move should be delayed until a subsequent trigger.
        The movement type once triggered is selected with ``input_mode``:

            * ``"move_relative"`` : Perform a relative move.
            * ``"move_absolute"`` : Perform an absolute move.
            * ``"home"`` : Perform a homing operation.
            * ``"disabled"`` : Do nothing.
        
        The output triggering logic is selected with ``output_logic``:

            * ``"high"`` : Output is high during the event.
            * ``"low"`` : Output is low during the event.

        The event for which the output trigger signal is sent is selected by ``output_mode``:

            * ``"in_motion"`` : Trigger activated during motion.
            * ``"motion_complete"`` : Trigger activated when motion is completed.
            * ``"max_velocity"`` : Trigger activated when movement reaches full speed.
            * ``"disabled"`` : Don't activate trigger.
        
        :param input_edge: Signal edge for input triggering.
        :param input_mode: Action to take on input trigger.
        :param output_logic: Output trigger logic level.
        :param output_mode: Event for which output trigger is activated.
        """
        # Note that all of the "mode" field is treated as a bit mask, which implies/allows for
        # multiple triggering actions. I'm assuming that is not actually possible, so the way
        # this is coded allows for only a single action on trigger.
        
        # TODO, actually use the current mode once that's implemented
        mode = 0

        # Set or clear the TRIGIN_HIGH bit
        # The documentation for this bit is horrible! We'll guess what it's supposed to mean...
        if input_edge == "rising":
            mode |= 0b00000001
        elif input_edge == "falling":
            mode &= 0b11111110
        elif input_edge is None:
            # Leave as is
            pass
        else:
            self._log.warn(f"Unrecognised trigger input_edge '{input_edge}'', should be 'rising' or 'falling'.")
        
        # Set one (only) of the TRIGIN_RELMOVE, TRIGIN_ABSMOVE or TRIGIN_HOMEMOVE bits
        if input_mode == "move_relative":
            mode &= 0b11110001
            mode |= 0b00000010
        elif input_mode == "move_absolute":
            mode &= 0b11110001
            mode |= 0b00000100
        elif input_mode == "home":
            mode &= 0b11110001
            mode |= 0b00001000
        elif input_mode == "disabled":
            mode &= 0b11110001
        elif input_mode is None:
            # Leave as is
            pass
        else:
            self._log.warn(f"Unrecognised trigger input_mode '{input_mode}', should be 'move_relative', 'move_absolute' or 'home'.")
        
        # Set or clear the TIGOUT_HIGH bit
        if output_logic == "high":
            mode |= 0b00010000
        elif output_logic == "low":
            mode &= 0b11101111
        elif output_logic is None:
            # Leave as is
            pass
        else:
            self._log.warn(f"Unrecognised trigger output_logic '{output_logic}', should be 'high' or 'low'")
        
        # Set one (only) of TRIGOUT_INMOTION, TRIGOUT_MOTIONCOMPLETE or TRIGOUT_MAXVELOCITY bits
        if output_mode == "in_motion":
            mode &= 0b00011111
            mode |= 0b00100000
        elif output_mode == "motion_complete":
            mode &= 0b00011111
            mode |= 0b01000000
        elif output_mode == "max_velocity":
            mode &= 0b00011111
            mode |= 0b10000000
        elif output_mode == "disabled":
            mode &= 0b00011111
        elif output_mode is None:
            # Leave as is
            pass
        else:
            self._log.warn(f"Unrecognised trigger output_mode '{output_mode}', should be 'in_motion', 'motion_complete' or 'max_velocity'.")
        
        self._log.debug(f"Setting trigger mode={mode} [bay={self.bays[bay]:#x}, channel={self.channels[channel]}].")
        self._loop.call_soon_threadsafe(self._write, apt.mot_set_trigger(source=EndPoint.HOST, dest=self.bays[bay], chan_ident=self.channels[channel], mode=mode))
        # Update status with new trigger parameters
        self._loop.call_soon_threadsafe(self._write, apt.mot_req_trigger(source=EndPoint.HOST, dest=self.bays[bay], chan_ident=self.channels[channel]))



