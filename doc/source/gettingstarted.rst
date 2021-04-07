Getting Started
===============

Prerequisites
-------------

Dependencies for thorlabs_apt_device are the python serial library (pyserial) and
thorlabs-apt-protocol, both of which should be installed automatically if using pip or similar.
If obtaining the code by other means, ensure they are installed and can be found in your python path.

Installing the Software
-----------------------

Download Using Pip
^^^^^^^^^^^^^^^^^^

The package installer for Python (pip) is the typical method for installation:

.. code-block:: sh

    pip install --user --upgrade thorlabs_apt_device

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


Usage
-----

.. code-block:: python

    # For a device based on a DC motor, such as a translation stage
    from thorlabs_apt_device import APTDevice_DC
    # On Windows, your serial port may be called COM3, COM5 etc.
    stage = APTDevice_DC("/dev/ttyUSB0")

    # Flash the LED on the device to identify it (default is first bay/channel)
    stage.identify()

    # Do some moves (encoder counts)
    stage.move_relative(20000)
    # or
    # stage.move_absolute(12345)

    # See all the status fields of the device
    print(stage.status_)

    # See the position of first bay and channel (in encoder counts)
    print(stage.status_[0][0]["position"])

    # Register for callbacks in case the device reports an error
    def error_callback(source, msgid, code, notes):
        # Hopefully never see this!
        print(f"Device {source} reported error code {code}: {note}")
    stage.register_error_callback(error_callback)




