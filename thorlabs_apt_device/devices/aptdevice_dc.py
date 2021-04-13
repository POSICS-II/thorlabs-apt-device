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

__all__ = ["APTDevice_DC"]

from .. import protocol as apt
from .aptdevice import APTDevice
from ..enums import EndPoint

class APTDevice_DC(APTDevice):
    """
    Initialise and open serial device for a ThorLabs APT controller based on a DC motor drive,
    such as a linear translation stage.

    :param serial_port: Serial port device the device is connected to.
    :param serial_number: Regular expression matching the serial number of device to search for.
    :param home: Perform a homing operation on initialisation.
    :param invert_direction_logic: Invert the meaning of "forward" and "reverse".
    :param swap_limit_switches: Swap "forward" and "reverse" limit switch values.
    :param controller: The destination :class:`EndPoint <thorlabs_apt_device.enums.EndPoint>` for the controller.
    :param bays: Tuple of :class:`EndPoint <thorlabs_apt_device.enums.EndPoint>`\\ (s) for the populated controller bays.
    :param channels: Tuple of indices (1-based) for the controller bay's channels.
    """

    def __init__(self, serial_port=None, serial_number="", home=True, invert_direction_logic=False, swap_limit_switches=False, controller=EndPoint.RACK, bays=(EndPoint.BAY0,), channels=(1,)):

        super().__init__(serial_port=serial_port, serial_number=serial_number, controller=controller, bays=bays, channels=channels)

        self.invert_direction_logic = invert_direction_logic
        """
        On some devices, "forward" velocity moves towards negative encoder counts.
        If that seems opposite to what is expected, this flag allows inversion of that logic.
        This will also swap the meaning of the ``"moving_forward"`` and ``"moving_reverse"`` 
        fields in the :data:`status` flags.
        """

        self.swap_limit_switches = swap_limit_switches
        """
        On some devices, the "forward" limit switch triggers when hitting the limit in the negative
        encoder count direction, and the "reverse" limit switch triggers towards positive encoder 
        counts.
        If that seems opposite to what is expected, this flag swaps the values of the
        ``"forward_limit_switch"`` and ``"reverse_limit_switch"`` fields in the :data:`status`
        flags.

        Note that this is independent of :data:`invert_direction_logic`.
        A stage may report it is "moving forward" (towards either positive or negative encoder
        counts), and then trigger the "reverse" limit switch.
        """

        self.status_ = [[{
            "position" : 0,
            "velocity": 0.0,
            "forward_limit_switch" : False,
            "reverse_limit_switch" : False,
            "moving_forward" : False,
            "moving_reverse" : False,
            "jogging_forward" : False,
            "jogging_reverse" : False,
            "motor_connected" : False,
            "homing" : False,
            "homed" : False,
            "tracking" : False,
            "interlock" : False,
            "settled" : False,
            "motion_error" : False,
            "motor_current_limit_reached" : False,
            "channel_enabled" : False,
            # Update message fields
            "msg" : "",
            "msgid" : 0,
            "source" : 0,
            "dest" : 0,
            "chan_ident" : 0,
        } for _ in self.channels] for _ in self.bays]
        """
        Array of dictionaries of status information for the bays and channels of the device.

        As a device may have multiple card bays, each with multiple channels, this data structure
        is an array of array of dicts. The first axis of the array indexes the bay, the second
        indexes the channel.
        For example, stage.status_[0][1] will return the status dictionary for the first bay, second
        channel.

        Keys for the dictionary are ``"position"``, ``"velocity"``, ``"forward_limit_switch"``,
        ``"reverse_limit_switch"``, ``"moving_forward"``, ``"moving_reverse"``,
        ``"jogging_forward"``, ``"jogging_reverse"``, ``"motor_connected"``, ``"homing"``,
        ``"homed"``, ``"tracking"``, ``"interlock"``, ``"settled"``, ``"motion_error"``,
        ``"motor_current_limit_reached"``, and ``"channel_enabled"``.
        Note that not all keys are relevant to every device.
        
        The documentation states that position is measured in encoder counts, but velocity is
        returned in real units of mm/second.

        Additionally, information about the most recent status message which updated the
        dictionary are also available as ``"msgid"``, ``"source"``, ``"dest"``, and
        ``"chan_ident"``.
        """
        # Status updates are received automatically (configured by APTDevice super class)
        
        self.velparams_ = [[{
            "min_velocity" : 0,
            "max_velocity" : 0,
            "acceleration" : 0,
            # Update message fields
            "msg" : "",
            "msgid" : 0,
            "source" : 0,
            "dest" : 0,
            "chan_ident" : 0,
        } for _ in self.channels] for _ in self.bays]
        """
        Array of dictionaries of velocity parameters.

        As a device may have multiple card bays, each with multiple channels, this data structure
        is an array of array of dicts. The first axis of the array indexes the bay, the second
        indexes the channel.

        Keys are ``"min_velocity"``, ``"max_velocity"``, and ``"acceleration"``.
        Units are encoder counts/second for velocities and counts/second/second for acceleration.
        """
        # Request current velocity parameters
        for bay in self.bays:
            for channel in self.channels:
                self._loop.call_soon_threadsafe(self._write, apt.mot_req_velparams(source=EndPoint.HOST, dest=bay, chan_ident=channel))
        

        self.genmoveparams_ = [[{
            "backlash_distance" : 0,
            # Update message fields
            "msg" : "",
            "msgid" : 0,
            "source" : 0,
            "dest" : 0,
            "chan_ident" : 0,
        } for _ in self.channels] for _ in self.bays]
        """
        Array of dictionaries of general move parameters.

        As a device may have multiple card bays, each with multiple channels, this data structure
        is an array of array of dicts. The first axis of the array indexes the bay, the second
        indexes the channel.

        The only documented parameter is the backlash compensation move distance,
        ``"backlash_distance"``, measured in encoder counts.
        """
        # Request current general move parameters
        for bay in self.bays:
            for channel in self.channels:
                self._loop.call_soon_threadsafe(self._write, apt.mot_req_genmoveparams(source=EndPoint.HOST, dest=bay, chan_ident=channel))


        self.jogparams_ = [[{
            "jog_mode" : 0,
            "step_size" : 0,
            "min_velocity" : 0,
            "acceleration" : 0,
            "max_velocity" : 0,
            "stop_mode" : 0,
            # Update message fields
            "msg" : "",
            "msgid" : 0,
            "source" : 0,
            "dest" : 0,
            "chan_ident" : 0,
        } for _ in self.channels] for _ in self.bays]
        """
        Array of dictionaries of jog parameters.

        As a device may have multiple card bays, each with multiple channels, this data structure
        is an array of array of dicts. The first axis of the array indexes the bay, the second
        indexes the channel.

        Keys are ``"jog_mode"``, ``"step_size"``, ``"min_velocity"``, ``"acceleration"``,
        ``"max_velocity"``, and "stop_mode".
        """
        # Request current jog parameters
        for bay in self.bays:
            for channel in self.channels:
                self._loop.call_soon_threadsafe(self._write, apt.mot_req_jogparams(source=EndPoint.HOST, dest=bay, chan_ident=channel))

        # Home each device if requested
        if home:
            for bay_i, _ in enumerate(self.bays):
                for channel_i, _ in enumerate(self.channels):
                    self.set_enabled(True, bay=bay_i, channel=channel_i)
                    # Sending enabled then home immediately on the TDC001 locks it up.
                    #self.home(bay=bay_i, channel=channel_i)
                    self._loop.call_later(1.0, self.home, bay_i, channel_i)


    def _process_message(self, m):
        super()._process_message(m)
        
        # Decode bay and channel IDs and check if they match one of ours
        if m.msg in ("mot_get_dcstatusupdate", "mot_move_stopped", "mot_move_completed", 
                     "mot_get_velparams",
                     "mot_get_genmoveparams", "mot_genmoveparams",
                     "mot_get_jogparams",
                     "mot_get_avmodes"):
            if m.source == EndPoint.USB:
                # Map USB controller endpoint to first bay
                bay_i = 0
            else:
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
        
        # Act on each message type
        if m.msg in ("mot_get_dcstatusupdate", "mot_move_stopped", "mot_move_completed"):
            # DC motor status update message    
            self.status_[bay_i][channel_i].update(m._asdict())
            # Scale velocity so it should be in mm/second
            # The explaination of scaling in the documentation doesn't make sense, but
            # dividing the returned value by 2.048 seems sensible (or by 2048 to give m/s)
            self.status_[bay_i][channel_i]["velocity"] /= 2.048
            # Swap meaning of "moving foward" and "moving reverse" if requested
            if self.invert_direction_logic:
                tmp = self.status_[bay_i][channel_i]["moving_forward"]
                self.status_[bay_i][channel_i]["moving_forward"] = self.status_[bay_i][channel_i]["moving_reverse"]
                self.status_[bay_i][channel_i]["moving_reverse"] = tmp
            # Swap values of limit switches if requested
            if self.swap_limit_switches:
                tmp = self.status_[bay_i][channel_i]["forward_limit_switch"]
                self.status_[bay_i][channel_i]["forward_limit_switch"] = self.status_[bay_i][channel_i]["reverse_limit_switch"]
                self.status_[bay_i][channel_i]["reverse_limit_switch"] = tmp
        elif m.msg == "mot_get_velparams":
            # Velocity parameter update
            self.velparams_[bay_i][channel_i].update(m._asdict())
        elif m.msg in ("mot_get_genmoveparams", "mot_genmoveparams"):
            # General move parameter update
            self.genmoveparams_[bay_i][channel_i].update(m._asdict())
        elif m.msg == "mot_get_jogparams":
            # Jog move parameter update
            self.jogparams_[bay_i][channel_i].update(m._asdict())
        else:
            #self._log.debug(f"Received message (unhandled): {m}")
            pass


    def home(self, bay=0, channel=0):
        """
        Home the device.

        :param bay: Index (0-based) of controller bay to send the command.
        :param channel: Index (0-based) of controller bay channel to send the command.
        """
        self._log.debug(f"Homing [bay={self.bays[bay]:#x}, channel={self.channels[channel]}].")
        self._loop.call_soon_threadsafe(self._write, apt.mot_move_home(source=EndPoint.HOST, dest=self.bays[bay], chan_ident=self.channels[channel]))


    def move_relative(self, distance=None, now=True, bay=0, channel=0):
        """
        Perform a relative move.

        :param distance: Movement amount in encoder steps.
        :param now: Perform movement immediately, or wait for subsequent trigger.
        :param bay: Index (0-based) of controller bay to send the command.
        :param channel: Index (0-based) of controller bay channel to send the command.
        """
        if now == True:
            self._log.debug(f"Relative move by {distance} steps [bay={self.bays[bay]:#x}, channel={self.channels[channel]}].")
            self._loop.call_soon_threadsafe(self._write, apt.mot_move_relative(source=EndPoint.HOST, dest=self.bays[bay], chan_ident=self.channels[channel], distance=distance))
        elif now == False and (not distance is None):
            self._log.debug(f"Preparing relative move by {distance} steps [bay={self.bays[bay]:#x}, channel={self.channels[channel]}].")
            self._loop.call_soon_threadsafe(self._write, apt.mot_set_moverelparams(source=EndPoint.HOST, dest=self.bays[bay], chan_ident=self.channels[channel], relative_distance=distance))
        else:
            # Don't move now, and no distance specified...
            self._log.warning("Requested a move_relative with now=False and distance=None: This does nothing!")


    def move_absolute(self, position=None, now=True, bay=0, channel=0):
        """
        Perform an absolute move.

        :param position: Movement destination in encoder steps.
        :param now: Perform movement immediately, or wait for subsequent trigger.
        :param bay: Index (0-based) of controller bay to send the command.
        :param channel: Index (0-based) of controller bay channel to send the command.
        """
        if now == True:
            self._log.debug(f"Absolute move to {position} steps [bay={self.bays[bay]:#x}, channel={self.channels[channel]}].")
            self._loop.call_soon_threadsafe(self._write, apt.mot_move_absolute(source=EndPoint.HOST, dest=self.bays[bay], chan_ident=self.channels[channel], position=position))
        elif now == False and (not position is None):
            self._log.debug(f"Preparing absolute move to {position} steps [bay={self.bays[bay]:#x}, channel={self.channels[channel]}].")
            self._loop.call_soon_threadsafe(self._write, apt.mot_set_moveabsparams(source=EndPoint.HOST, dest=self.bays[bay], chan_ident=self.channels[channel], absolute_position=position))
        else:
            # Don't move now, and no position specified...
            self._log.warning("Requested a move_absolute with now=False and position=None: This does nothing!")


    def stop(self, immediate=False, bay=0, channel=0):
        """
        Stop any current movement.

        :param immediate: Stop immediately, or using the profiled velocity curves.
        :param bay: Index (0-based) of controller bay to send the command.
        :param channel: Index (0-based) of controller bay channel to send the command.
        """
        # False == 2 == profiled, True == 1 == immediate
        stop_mode = (2, 1)[bool(immediate)]
        self._log.debug(f"Stopping {'immediately' if stop_mode == 1 else 'profiled'} [bay={self.bays[bay]:#x}, channel={self.channels[channel]}].")
        self._loop.call_soon_threadsafe(self._write, apt.mot_move_stop(source=EndPoint.HOST, dest=self.bays[bay], chan_ident=self.channels[channel], stop_mode=stop_mode))
    

    def move_velocity(self, direction="forward", bay=0, channel=0):
        """
        Start a movement at constant velocity in the specified direction.

        Direction can be specified as boolean, string or numerical:
        
            * ``False`` is reverse and ``True`` is forward.
            * ``reverse`` is reverse and any other string is forward.
            * ``0`` or ``2`` (or any even number) is reverse and ``1`` (or any odd number) is forward.

        :param direction: Direction to move (forward or reverse).
        :param bay: Index (0-based) of controller bay to send the command.
        :param channel: Index (0-based) of controller bay channel to send the command.
        """
        if type(direction) is bool:
            # False == 2 == reverse, True == 1 == forward
            direction = (2, 1)[direction]
        elif type(direction) is str:
            # forward unless specifically "reverse"
            direction = 2 if direction == "reverse" else 1
        elif type(direction) in (int, float):
            # forward = 1 (or odd numbers), reverse = 0 or 2 (even numbers)
            direction = 2 - int(direction)%2
        else:
            # Otherwise, default to forward
            self._log.warning("Requested a move_velocity with unknown direction \"{direction}\", defaulting to forward.")
            direction = 1
        self._log.debug(f"Velocity move {'forward' if direction == 1 else 'reverse'} [bay={self.bays[bay]:#x}, channel={self.channels[channel]}].")
        # Invert the forward=negative to forward=positive direction logic if requested
        direction = 2 - (direction + bool(self.invert_direction_logic))%2
        self._loop.call_soon_threadsafe(self._write, apt.mot_move_velocity(source=EndPoint.HOST, dest=self.bays[bay], chan_ident=self.channels[channel], direction=direction))


    def set_velocity_params(self, acceleration, max_velocity, bay=0, channel=0):
        """
        Configure the parameters for movement velocity.

        :param acceleration: Acceleration in counts/second/second.
        :param max_velocity: Maximum velocity in counts/second.
        :param bay: Index (0-based) of controller bay to send the command.
        :param channel: Index (0-based) of controller bay channel to send the command.
        """
        self._log.debug(f"Setting velocity parameters to accel={acceleration}, max={max_velocity} [bay={self.bays[bay]:#x}, channel={self.channels[channel]}].")
        self._loop.call_soon_threadsafe(self._write, apt.mot_set_velparams(source=EndPoint.HOST, dest=self.bays[bay], chan_ident=self.channels[channel], min_velocity=0, acceleration=acceleration, max_velocity=max_velocity))
        # Update status with new velocity parameters
        self._loop.call_soon_threadsafe(self._write, apt.mot_req_velparams(source=EndPoint.HOST, dest=self.bays[bay], chan_ident=self.channels[channel]))


    def set_enabled(self, state=True, bay=0, channel=0):
        """
        Enable or disable a device.

        :param state: Set to ``True`` for enable, ``False`` for disabled.
        :param bay: Index (0-based) of controller bay to send the command.
        :param channel: Index (0-based) of controller bay channel to send the command.
        """
        state = (2, 1)[bool(state)]
        self._log.debug(f"Setting channel enabled={state == 1} [bay={self.bays[bay]:#x}, channel={self.channels[channel]}].")
        self._loop.call_soon_threadsafe(self._write, apt.mod_set_chanenablestate(source=EndPoint.HOST, dest=self.bays[bay], chan_ident=self.channels[channel], enable_state=state))


    def set_jog_params(self, size, acceleration, max_velocity, continuous=False, immediate_stop=False, bay=0, channel=0):
        """
        Configure the parameters for jogging movements.

        :param size: Size of movement in encoder counts.
        :param acceleration: Acceleration in counts/second/second.
        :param max_velocity: Maximum velocity in counts/second.
        :param continuous: Continuous movement, or single step.
        :param immediate_stop: Stop immediately, or using the profiled velocity curves.
        :param bay: Index (0-based) of controller bay to send the command.
        :param channel: Index (0-based) of controller bay channel to send the command.
        """
        # False == 2 == profiled, True == 1 == immediate
        stop_mode = (2, 1)[bool(immediate_stop)]
        # False == 2 == stepped, True == 1 == continuous
        jog_mode = (2, 1)[bool(continuous)]
        self._log.debug(f"Setting jog parameters to size={size}, accel={acceleration}, max={max_velocity}, cont={continuous}, imm={immediate_stop} [bay={self.bays[bay]:#x}, channel={self.channels[channel]}].")
        self._loop.call_soon_threadsafe(self._write, apt.mot_set_jogparams(source=EndPoint.HOST, dest=self.bays[bay], chan_ident=self.channels[channel], step_size=size, min_velocity=0, acceleration=acceleration, max_velocity=max_velocity, jog_mode=jog_mode, stop_mode=stop_mode))
        # Update status with new jog parameters
        self._loop.call_soon_threadsafe(self._write, apt.mot_req_jogparams(source=EndPoint.HOST, dest=self.bays[bay], chan_ident=self.channels[channel]))


    def move_jog(self, direction="forward", bay=0, channel=0):
        """
        Start a jog movement in the specified direction.

        Direction can be specified as boolean, string or numerical:
        
            * ``False`` is reverse and ``True`` is forward.
            * ``reverse`` is reverse and any other string is forward.
            * ``0`` or ``2`` (or any even number) is reverse and ``1`` (or any odd number) is forward.

        :param direction: Direction to move (forward or reverse).
        :param bay: Index (0-based) of controller bay to send the command.
        :param channel: Index (0-based) of controller bay channel to send the command.
        """
        if type(direction) is bool:
            # False == 2 == reverse, True == 1 == forward
            direction = (2, 1)[direction]
        elif type(direction) is str:
            # forward unless specifically "reverse"
            direction = 2 if direction == "reverse" else 1
        elif type(direction) in (int, float):
            # forward = 1 (or odd numbers), reverse = 0 or 2 (even numbers)
            direction = 2 - int(direction)%2
        else:
            # Otherwise, default to forward
            self._log.warning("Requested a move_jog with unknown direction \"{direction}\", defaulting to forward.")
            direction = 1
        self._log.debug(f"Jog move {'forward' if direction == 1 else 'reverse'} [bay={self.bays[bay]:#x}, channel={self.channels[channel]}].")
        # Invert the forward=negative to forward=positive direction logic if requested
        direction = 2 - (direction + bool(self.invert_direction_logic))%2
        self._loop.call_soon_threadsafe(self._write, apt.mot_move_jog(source=EndPoint.HOST, dest=self.bays[bay], chan_ident=self.channels[channel], direction=direction))


    def set_move_params(self, backlash_distance, bay=0, channel=0):
        """
        Set parameters for generic move commands, currently only the backlash compensation distance.

        :param backlash_distance: Backlash compensation distance in encoder counts.
        :param bay: Index (0-based) of controller bay to send the command.
        :param channel: Index (0-based) of controller bay channel to send the command.
        """
        self._log.debug(f"Setting move parameters to backlash={backlash_distance} steps [bay={self.bays[bay]:#x}, channel={self.channels[channel]}].")
        self._loop.call_soon_threadsafe(self._write, apt.mot_set_genmoveparams(source=EndPoint.HOST, dest=self.bays[bay], chan_ident=self.channels[channel], backlash_distance=backlash_distance))
        # Update status with new general move parameters
        self._loop.call_soon_threadsafe(self._write, apt.mot_req_genmoveparams(source=EndPoint.HOST, dest=self.bays[bay], chan_ident=self.channels[channel]))
