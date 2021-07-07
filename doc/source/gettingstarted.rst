Getting Started
===============

Prerequisites
-------------

The only dependency for thorlabs_apt_device is the python serial library
(`pyserial <https://pypi.org/project/pyserial/>`_) which should be installed automatically if using pip or similar.
If obtaining the code by other means, ensure it is installed and can be found in your python path.

Installing the Software
-----------------------

Download Using Pip
^^^^^^^^^^^^^^^^^^

The package installer for Python (pip) is the typical method for installation:

.. code-block:: sh

    pip install --user --upgrade thorlabs-apt-device

The ``--user`` parameter installs using user-level permissions, thus does not require root or administrator privileges.
To install system wide, remove the ``--user`` parameter and prefix the command with ``sudo`` (Linux, MacOS), or run as administrator (Windows).

Clone From Git
^^^^^^^^^^^^^^

Alternatively, the latest version can be downloaded from the git repository:

.. code-block:: sh

    git clone https://gitlab.com/ptapping/thorlabs-apt-device.git

and optionally installed to your system using ``pip``:

.. code-block:: sh

    pip install --user ./thorlabs-apt-device


Windows Only: Enable Virtual COM Port
--------------------------------------

On Windows, the virtual serial communications port (VCP) may need to be enabled in the driver
options for the USB interface device.
First, open the Windows Device Manager.
If plugging in the controller causes a new COM device to appear under the "Ports (COM & LPT)"
section, then there is nothing more to do.
If a new COM device does not appear, then find the controller device under "Universal Serial Bus
Controllers", it may be called "Thorlabs APT Controller" or similar (see what new device appears
when plugging in the controller).
Right-click->Properties->Advanced tab, check the "Load VCP" box, then OK out of the dialog back to
the device manager.
Unplug and re-plug the USB connection to the controller, and ensure than a new COM device now
appears.


Usage
-----

.. code-block:: python

    # The BBD201 DC motor controller has a dedicated class which handles its specifics
    from thorlabs_apt_device import BBD201

    # You can try to find a device automatically:
    stage = BBD201()
    # Or, if you know the serial number of the device starts with "73123":
    # stage = BBD201(serial_number="73123")
    # You can also specify the serial port device explicitly.
    # On Windows, your serial port may be called COM3, COM5 etc.
    # stage = BBD201("/dev/ttyUSB0")

    # Flash the LED on the device to identify it
    stage.identify()

    # Do some moves (encoder counts)
    stage.move_relative(20000)
    # or
    # stage.move_absolute(12345)

    # See all the status fields of the device
    print(stage.status)

    # See the position (in encoder counts)
    print(stage.status["position"])

    # Register for callbacks in case the device reports an error
    def error_callback(source, msgid, code, notes):
        # Hopefully never see this!
        print(f"Device {source} reported error code {code}: {note}")
    stage.register_error_callback(error_callback)

See the documentation for the :mod:`~thorlabs_apt_device.utils` module for methods for converting real world units
into your specific device's encoder counts.


