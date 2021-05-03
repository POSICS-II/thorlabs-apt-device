Welcome to thorlabs_apt_device's documentation!
===============================================

This is a python interface to Thorlabs equipment which communicates using the APT protocol.
Because there are a large variety of these devices, such as translation and rotation stages,
flip mounts and laser diode drivers, this package has been kept as general as possible.
A hierarchical class structure is designed such that basic functionality is handled transparently 
at low levels, allowing a minimal amount of code to be used to implement device-specific features.

In its current state, this package should be able to perform device discovery, communications and
message encoding/decoding for every APT-compatible device.
Classes for a small number of specific motion controllers are provided which give essentially
feature complete functionality for these particular devices.
To use a new, unsupported device, a subclass can be created which describes the specifics of
the device control and implement its new functionality.
If the device is very similar to something already implemented, then the amount of coding required
can be very small.
For example, the :mod:`TDC001 <thorlabs_apt_device.devices.tdc001>` is a relatively simple DC motor driven
motion controller, and the class to implement it is only a few lines of code since it is able to
be derived from the :mod:`DC motor class <thorlabs_apt_device.devices.aptdevice_dc>`.


User Guide
----------

.. toctree::
   :maxdepth: 2

   gettingstarted

API Documentation
-----------------
.. toctree::
   :maxdepth: 5
   :titlesonly:

   api/thorlabs_apt_device


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
