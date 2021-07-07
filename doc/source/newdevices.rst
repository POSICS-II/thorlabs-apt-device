Supporting a New Device
=======================

It is likely that the specific Thorlabs APT device you wish to control does not already have a
specific class associated with it, and so you will need to write some code to support it.
However, the layout of the library has been designed to try and minimise the amount of code
required for new devices.

Class Hierarchy
---------------

The most fundamental features common to all devices is handled in the ``APTDevice`` main parent
class.
Sub-classes extend this to implement additional functionality.
For example, the ``APTDevice_Motor`` class implements features related to motor-driven devices.
Finally, classes like ``BSC201_DRV250`` are specific to the BSC201 controller paired with the
DRV250 linear actuator.

Supporting a new device starts by identifying a class which already implements the most number of
features, and then creating a new extension class.