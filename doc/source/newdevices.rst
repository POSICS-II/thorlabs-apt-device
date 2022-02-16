Supporting a New Device
=======================

It is likely that the specific Thorlabs APT device you wish to control does not already have a
specific class associated with it, and so you will need to write some code to support it.
However, the layout of the library has been designed to try and minimise the amount of code
required for new devices.

APT Communications Protocol
---------------------------

All APT protocol messages are able to be encoded and decoded by the help of the
:data:`~thorlabs_apt_device.protocol` package. The details of these messages, and their
applicability to particular hardware devices, is documented in the `APT Communications Protocol
<https://www.thorlabs.com/Software/Motion%20Control/APT_Communications_Protocol.pdf>`__ PDF document
on the Thorlabs website.

Class Hierarchy
---------------

The most fundamental features common to all devices is handled in the
:data:`~thorlabs_apt_device.devices.aptdevice.APTDevice` main parent class. Sub-classes extend this
to implement additional functionality. For example, the
:data:`~thorlabs_apt_device.devices.aptdevice_motor.APTDevice_Motor` class implements features
related to motor-driven devices. A further subclass such as
:data:`~thorlabs_apt_device.devices.bsc.BSC` supports the series of benchtop stepper motor
controllers. Finally, classes like :data:`~thorlabs_apt_device.devices.bsc.BSC201_DRV250` are
specific to the BSC201 controller paired with the DRV250 linear actuator.

Supporting a new device starts by identifying a class which already implements the most number of
features, and then creating a new extension class.