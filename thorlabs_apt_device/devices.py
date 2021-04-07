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

"""
Classes to interface to devices which communicate using the ThorLabs APT protocol.
"""

import logging
import asyncio
from threading import Thread
import atexit

import serial
import thorlabs_apt_protocol as apt

from .enums import EndPoint
from .unpacker import Unpacker

class APTDevice():

    def __init__(self, serial_port, controller=EndPoint.RACK, bays=(EndPoint.BAY0,), channels=(1,)):
        """
        Initialise and open serial device for the ThorLabs APT controller.

        :param serial_port: The serial port where the device is attached.
        :param controller: The destination :class:`EndPoint` for the controller.
        :param bays: Tuple of :class:`EndPoint`(s) for the populated controller bays.
        :param channels: Tuple of indices (1-based) for the controller bay's channels.
        """

        self._log = logging.getLogger(__name__)
        self._log.info(f"Initialising serial port ({serial_port}).")
        # Open and configure serial port settings for ThorLabs APT controllers
        self._port = serial.Serial(serial_port,
                                baudrate=115200,
                                bytesize=serial.EIGHTBITS,
                                parity=serial.PARITY_NONE,
                                stopbits=serial.STOPBITS_ONE,
                                timeout=0.1,
                                rtscts=False)
        self._port.rts = True
        self._port.reset_input_buffer()
        self._port.reset_output_buffer()
        self._port.rts = False
        self._log.info("Opened serial port OK.")

        # APT protocol unpacker for decoding received messages
        self._unpacker = Unpacker(self._port, on_error="warn")

        # ID numbers for controller, bay device and channel identification
        """ID code for the controller message :class:`EndPoint`."""
        self.controller = controller
        """Tuple of ID codes for the controller's card bay :class:`EndPoints`."""
        self.bays = bays
        """Tuple of indexes for the the channels in card bays."""
        self.channels = channels

        # List of functions to call when error notifications recieved
        self._error_callbacks = set()

        # Create a new event loop for ourselves to queue and send commands
        self._loop = asyncio.new_event_loop()

        # Schedule the first check for incoming data on the serial port
        self._loop.call_soon(self._schedule_reads)
        """Time to wait between read attempts on the serial port, in seconds."""
        self.read_interval = 0.01

        # Schedule sending of the "keep alive" acknowledgement commands
        self._loop.call_soon(self._schedule_keepalives)
        """Time interval between sending of keepalive commands, in seconds."""
        self.keepalive_interval = 0.9

        # Request the controller to start sending regular status updates
        for bay in self.bays:
            self._loop.call_soon(self._write, apt.hw_start_updatemsgs(source=EndPoint.HOST, dest=bay))

        # Create a new thread to run the event loop in
        self._thread = Thread(target=self._run_eventloop)
        # Set as daemon thread so it can be killed automatically at program exit
        self._thread.daemon = True
        self._thread.start()

        # Close the serial port at exit in case close() wasn't called
        atexit.register(self._atexit)


    def _run_eventloop(self):
        """
        Entry point for the event loop thread.
        """
        self._log.debug("Starting event loop.")
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_forever()
        finally:
            self._loop.close()
            self._loop = None
        self._log.debug("Event loop stopped.")
        self._close_port()


    def _close_port(self):
        """
        Stop status messages and then close the serial port connection to the controller.
        """
        if self._port is not None:
            self._log.debug("Stopping hardware update messages.")
            try:
                for bay in self.bays:
                    self._write(apt.hw_stop_updatemsgs(source=EndPoint.HOST, dest=bay))
                # Don't know if the disconnect message actually does anything, but might as well send it
                self._log.debug("Sending disconnect notification.")
                self._write(apt.hw_disconnect(source=EndPoint.HOST, dest=self.controller))
            except:
                # Something wrong writing to the port, ignore
                self._log.debug("Unable to send disconnect messages.")
                pass
            self._log.info("Closing serial connection.")
            self._port.close()
            self._port = None


    def _atexit(self):
        """
        Catch exit signal and attempt to close everything gracefully.
        """
        # Request the event loop to stop
        self.close()
        # Wait for event loop thread to finish
        self._thread.join()


    def _write(self, command_bytes):
        """
        Write a command out the the serial port.

        :param command_bytes: Command to send to the device as raw byte array.
        """
        #self._log.debug(f"Writing command bytes: {command_bytes}")
        self._port.write(command_bytes)
        self._port.flush()


    def _schedule_reads(self):
        """
        Check for any incoming messages and process them at regular intervals.
        """
        #self._log.debug(f"Checking for data on serial port.")
        for msg in self._unpacker:
            #self._log.debug(f"Received message: {msg}")
            self._process_message(msg)
        # Schedule next check
        self._loop.call_later(self.read_interval, self._schedule_reads)


    def _schedule_keepalives(self):
        """
        Send the "keep alive" acknowledgement command at regular intervals.
        """
        #self._log.debug(f"Sending keep alive acknowledgement.")
        for bay in self.bays:
            self._loop.call_soon(self._write, apt.mot_ack_dcstatusupdate(source=EndPoint.HOST, dest=bay))
        # Schedule next send
        self._loop.call_later(self.keepalive_interval, self._schedule_keepalives)


    def _process_message(self, m):
        """
        Process a single response message from the controller.

        :param m: The unpacked message from the controller.
        """
        # TODO: Process any messages common to all APT controllers (which ones?)
        if m.msg == "hw_response":
            # Should there be an error code? The documentation is a little unclear
            self._log.warn(f"Received unknown event notification from APT device {m.source}.")
            for callback in self._error_callbacks:
                callback(source=m.source, msgid=0, code=-1, notes="unknown")
        elif m.msg == "hw_rich_response":
            self._log.warn(f"Received event notification code {m.code} from APT device {m.source}: {m.notes}")
            for callback in self._error_callbacks:
                callback(source=m.source, msgid=m.msgid, code=m.code, notes=m.notes)


    def register_error_callback(self, callback_function):
        """
        Register a function to be called in the case of an error being reported by the device.

        The function passed in should have the signature ``callback_function(source, msgid, code, notes)``,
        where ``source`` is the :class:`EndPoint` where the message originated, ``msgid`` is the 
        type of message which triggered the error (or 0 if unknown or a spontaneous error),
        ``code`` is a numerical error code and ``notes`` is a string description.

        :params callback_function: Function to call in case of device error.
        """
        if callable(callback_function):
            self._error_callbacks.add(callback_function)
        else:
            self._log.warn("Attempted to register a non-callable object as a callback function.")
    

    def unregister_error_callback(self, callback_function):
        """
        Unregister a previously registered error callback function.

        The function passed in should have been previously registered using :meth:`register_error_callback`.

        :params callback_function: Function to unregister.
        """
        if callback_function not in self._error_callbacks:
            self._log.warn("Attemped to unregister an unknown function.")
        else:
            self._error_callbacks.pop(callback_function)


    def close(self):
        """
        Close the serial connection to the ThorLabs APT controller.
        """
        if self._loop is not None:
            self._log.debug("Stopping event loop.")
            self._loop.call_soon_threadsafe(self._loop.stop)
        # Note, this returns before event loop has actually stopped and serial port closed


    def identify(self, channel=None):
        """
        Flash the device's front panel LEDs to identify the unit.

        In card-slot (bay) controllers, the LED is on the front of the controller, not the individual cards, and ``channel=None`` should be used.

        :param channel: Index (0-based) of controller bay channel to send the command.
        """
        if channel is None:
            self._log.debug("Identifying [channel=None].")
            self._loop.call_soon_threadsafe(self._write, apt.mod_identify(source=EndPoint.HOST, dest=EndPoint.USB, chan_ident=0))
        else:
            self._log.debug(f"Identifying [channel={self.channels[channel]}].")
            self._loop.call_soon_threadsafe(self._write, apt.mod_identify(source=EndPoint.HOST, dest=EndPoint.RACK, chan_ident=self.channels[channel]))
        

class APTDevice_DC(APTDevice):

    def __init__(self, serial_port, home=True, invert_direction_logic=True, controller=EndPoint.RACK, bays=(EndPoint.BAY0,), channels=(1,)):
        """
        Initialise and open serial device for a ThorLabs APT controller based on a DC motor drive,
        such as a linear translation stage.

        :param serial_port: The serial port where the device is attached.
        :param home: Perform a homing operation on initialisation.
        :param invert_direction_logic: Invert the meaning of "forward" and "reverse".
        :param controller: The destination :class:`EndPoint` for the controller.
        :param bays: Tuple of :class:`EndPoint`(s) for the populated controller bays.
        :param channels: Tuple of indices (1-based) for the controller bay's channels.
        """
        super().__init__(serial_port, controller=controller, bays=bays, channels=channels)

        """
        On some devices, "forward" velocity moves towards negative encoder counts.
        If that seems opposite to what is expected, this flag allows inversion of that logic.
        This will also swap the meaning of "forward" and "reverse" limit switches to match the
        movement direction.
        """
        self.invert_direction_logic = invert_direction_logic

        """
        Array of dictionaries of status information for the bays and channels of the device.

        As a device may have multiple card bays, each with multiple channels, this data structure
        is an array of array of dicts. The first axis of the array indexes the bay, the second
        indexes the channel.
        For example, stage.status[0][1] will return the status dictionary for the first bay, second
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
        self.status = [[{
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
        }]*len(self.channels)]*len(self.bays)
        # Status updates are received automatically (configured by APTDevice super class)
        
        """
        Array of dictionaries of velocity parameters.

        As a device may have multiple card bays, each with multiple channels, this data structure
        is an array of array of dicts. The first axis of the array indexes the bay, the second
        indexes the channel.

        Keys are ``"min_velocity"``, ``"max_velocity"``, and ``"acceleration"``.
        Units are encoder counts/second for velocities and counts/second/second for acceleration.
        """
        self.velparams = [[{
            "min_velocity" : 0,
            "max_velocity" : 0,
            "acceleration" : 0,
            # Update message fields
            "msg" : "",
            "msgid" : 0,
            "source" : 0,
            "dest" : 0,
            "chan_ident" : 0,
        }]*len(self.channels)]*len(self.bays)
        # Request current velocity parameters
        for bay in self.bays:
            for channel in self.channels:
                self._loop.call_soon_threadsafe(self._write, apt.mot_req_velparams(source=EndPoint.HOST, dest=bay, chan_ident=channel))

        """
        Array of dictionaries of general move parameters.

        As a device may have multiple card bays, each with multiple channels, this data structure
        is an array of array of dicts. The first axis of the array indexes the bay, the second
        indexes the channel.

        The only documented parameter is the backlash compensation move distance,
        ``"backlash_distance"``, measured in encoder counts.
        """
        self.genmoveparams = [[{
            "backlash_distance" : 0,
            # Update message fields
            "msg" : "",
            "msgid" : 0,
            "source" : 0,
            "dest" : 0,
            "chan_ident" : 0,
        }]*len(self.channels)]*len(self.bays)
        # Request current general move parameters
        for bay in self.bays:
            for channel in self.channels:
                self._loop.call_soon_threadsafe(self._write, apt.mot_req_genmoveparams(source=EndPoint.HOST, dest=bay, chan_ident=channel))

        """
        Array of dictionaries of jog parameters.

        As a device may have multiple card bays, each with multiple channels, this data structure
        is an array of array of dicts. The first axis of the array indexes the bay, the second
        indexes the channel.

        Keys are ``"jog_mode"``, ``"step_size"``, ``"min_velocity"``, ``"acceleration"``,
        ``"max_velocity"``, and "stop_mode".
        """
        self.jogparams = [[{
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
        }]*len(self.channels)]*len(self.bays)
        # Request current jog parameters
        for bay in self.bays:
            for channel in self.channels:
                self._loop.call_soon_threadsafe(self._write, apt.mot_req_jogparams(source=EndPoint.HOST, dest=bay, chan_ident=channel))

        """
        Array of LED mode bit fields as integers. See :class:`LEDMode` for details.
        
        As a device may have multiple card bays, each with multiple channels, this data structure
        is an array of array of dicts. The first axis of the array indexes the bay, the second
        indexes the channel.
        """
        self.avmodes = [[0]*len(self.channels)]*len(self.bays)
        # Request current LED modes
        for bay in self.bays:
            for channel in self.channels:
                self._loop.call_soon_threadsafe(self._write, apt.mot_req_avmodes(source=EndPoint.HOST, dest=bay, chan_ident=channel))

        # Home each device if requested
        if home:
            for bay_i, _ in enumerate(self.bays):
                for channel_i, _ in enumerate(self.channels):
                    self.home(bay=bay_i, channel=channel_i)


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
            self.status[bay_i][channel_i].update(m._asdict())
            # Scale velocity so it should be in mm/second
            # The explaination of scaling in the documentation doesn't make sense, but
            # dividing the returned value by 2.048 seems sensible (or by 2048 to give m/s)
            self.status[bay_i][channel_i]["velocity"] /= 2.048
        elif m.msg == "mot_get_velparams":
            # Velocity parameter update
            self.velparams[bay_i][channel_i].update(m._asdict())
        elif m.msg in ("mot_get_genmoveparams", "mot_genmoveparams"):
            # General move parameter update
            self.genmoveparams[bay_i][channel_i].update(m._asdict())
        elif m.msg == "mot_get_jogparams":
            # Jog move parameter update
            self.jogparams[bay_i][channel_i].update(m._asdict())
        elif m.msg == "mot_get_avmodes":
            # LED mode parameter update
            self.avmodes[bay_i][channel_i] = m.mode_bits
        else:
            self._log.debug(f"Received message (unhandled): {m}")


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


    def set_led_mode(self, mode_bits, bay=0, channel=0):
        """
        Configure the behaviour of the controller's status LEDs.

        The ``mode_bits`` can be generated by composing values from the :class:`LEDMode` enum.
        For example, ``LEDMode.IDENT | LEDMode.MOVING`` would set the LED to flash when the identify message is sent, and also when the motor is moving.

        :param mode_bits: Integer containing the relevant mode bits.
        :param bay: Index (0-based) of controller bay to send the command.
        :param channel: Index (0-based) of controller bay channel to send the command.
        """
        self._log.debug(f"Setting LED mode to mode_bits={mode_bits} [bay={self.bays[bay]:#x}, channel={self.channels[channel]}].")
        self._loop.call_soon_threadsafe(self._write, apt.mot_set_avmodes(source=EndPoint.HOST, dest=self.bays[bay], chan_ident=self.channels[channel], mode_bits=mode_bits))
        # Update status with new LED parameters
        self._loop.call_soon_threadsafe(self._write, apt.mot_req_avmodes(source=EndPoint.HOST, dest=self.bays[bay], chan_ident=self.channels[channel]))
