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

__all__ = ["APTDevice", "find_device"]

import logging
import asyncio
from threading import Thread
import atexit
import re

import serial
from serial.tools import list_ports, list_ports_common

from .. import protocol as apt
from ..enums import EndPoint, LEDMode

class APTDevice():
    """
    Initialise and open serial device for the ThorLabs APT controller.

    If the ``serial_port`` parameter is ``None`` (default), then an attempt to detect an APT device
    will be performed.
    The first device found will be initialised.
    If multiple devices are present on the system, then the use of the ``serial_number`` parameter
    will specify a particular device by its serial number.
    This is a `regular expression <https://docs.python.org/3/library/re.html>`_ match, for example
    ``serial_number="83"`` would match devices with serial numbers
    starting with 83, while ``serial_number=".*83$"`` would match devices ending in 83.

    :param serial_port: Serial port device the device is connected to.
    :param serial_number: Regular expression matching the serial number of device to search for.
    :param controller: The destination :class:`EndPoint <thorlabs_apt_device.enums.EndPoint>` for the controller.
    :param bays: Tuple of :class:`EndPoint <thorlabs_apt_device.enums.EndPoint>`\\ (s) for the populated controller bays.
    :param channels: Tuple of indices (1-based) for the controller bay's channels.
    """

    def __init__(self, serial_port=None, serial_number="", controller=EndPoint.RACK, bays=(EndPoint.BAY0,), channels=(1,)):
        
        # If serial_port not specified, search for a device
        if serial_port is None:
            serial_port = find_device(serial_number=serial_number)

        # Accept a serial.tools.list_ports.ListPortInfo object (which we may have just found)
        if isinstance(serial_port, list_ports_common.ListPortInfo):
            serial_port = serial_port.device
        
        if serial_port is None:
            raise RuntimeError(f"No Thorlabs APT devices detected with serial_number matching '{serial_number}'.")

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
        self._unpacker = apt.Unpacker(self._port, on_error="warn")

        # ID numbers for controller, bay device and channel identification
        self.controller = controller
        """ID code for the controller message :class:`EndPoint <thorlabs_apt_device.enums.EndPoint>`."""
        self.bays = bays
        """Tuple of ID codes for the controller's card bay :class:`EndPoint <thorlabs_apt_device.enums.EndPoint>`\\ (s)."""
        self.channels = channels
        """Tuple of indexes for the the channels in card bays."""

        # List of functions to call when error notifications recieved
        self._error_callbacks = set()

        # Create a new event loop for ourselves to queue and send commands
        self._loop = asyncio.new_event_loop()

        # Schedule the first check for incoming data on the serial port
        self._loop.call_soon(self._schedule_reads)
        self.read_interval = 0.01
        """Time to wait between read attempts on the serial port, in seconds."""

        # Schedule sending of the "keep alive" acknowledgement commands
        self._loop.call_soon(self._schedule_keepalives)
        self.keepalive_interval = 0.9
        """Time interval between sending of keepalive commands, in seconds."""

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
        where ``source`` is the :class:`enums.EndPoint` where the message originated, ``msgid`` is the 
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


    def identify(self, channel=0):
        """
        Flash the device's front panel LEDs to identify the unit.

        For some single-channel USB controlled devices ``channel=None`` is used,
        which sends the identify command to the USB controller :class:`EndPoint`.
        On devices which are considered "rack" controllers (including single-channel "rack" 
        units such as the BBD201), the ``channel`` parameter will actually refer to the card bay.
        There are likely other types of units (though currently untested) which have a single "bay"
        with multiple channels, and then the ``channel`` parameter would refer to the actual
        channel index of the controller card.

        :param channel: Index (0-based) of controller bay channel to send the command.
        """
        if channel is None:
            self._log.debug("Identifying [channel=None].")
            self._loop.call_soon_threadsafe(self._write, apt.mod_identify(source=EndPoint.HOST, dest=EndPoint.USB, chan_ident=0))
        else:
            self._log.debug(f"Identifying [channel={self.channels[channel]}].")
            self._loop.call_soon_threadsafe(self._write, apt.mod_identify(source=EndPoint.HOST, dest=EndPoint.RACK, chan_ident=self.channels[channel]))
 

def find_device(serial_number=""):
    """
    Search attached serial ports for a Thorlabs APT controller.

    The first device found will be returned.
    If multiple devices are attached to the system, the ``serial_number`` parameter may be used
    to select the correct device. This is a regular expression match, for example
    ``serial_number="83"`` would match devices with serial numbers starting with 83, while
    ``serial_number=".*83$"`` would match devices ending in 83.

    Note that the APT protocol documentation lists formats for device serial numbers.
    For example, a TDC001 "DC Driver T-Cube" should have serial numbers starting with "83".

    :param serial_number: Regular expression to match a device serial number.
    """
    for p in serial.tools.list_ports.comports():
        if re.match("Thorlabs", p.manufacturer) and p.product and re.match("APT", p.product) and re.match(serial_number, p.serial_number):
            return p