#!/usr/bin/env python3

from thorlabs_apt_device import APTDevice, BSC201_DRV250, find_device, list_devices, EndPoint, protocol
from serial.tools import list_ports
import logging
logging.basicConfig(level=logging.DEBUG)

stage = BSC201_DRV250()