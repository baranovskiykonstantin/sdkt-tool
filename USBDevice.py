#!/usr/bin/env python2
# -*-    Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4    -*-
### BEGIN LICENSE
# Copyright (C) 2012 <Baranovskiy Konstantin> <baranovskiykonstantin@gmail.com>
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranties of
# MERCHANTABILITY, SATISFACTORY QUALITY, or FITNESS FOR A PARTICULAR
# PURPOSE.  See the GNU General Public License for more details
#
# You should have received a copy of the GNU General Public License along
# with this program.  If not, see <http://www.gnu.org/licenses/>.
### END LICENSE

import usb
import sys

# bmRequestType
USB_ENDPOINT_IN          = 0x80
USB_ENDPOINT_OUT         = 0x00

USB_TYPE_STANDARD        = (0x00 << 5)
USB_TYPE_CLASS           = (0x01 << 5)
USB_TYPE_VENDOR          = (0x02 << 5)
USB_TYPE_RESERVED        = (0x03 << 5)

USB_RECIP_DEVICE         = 0x00
USB_RECIP_INTERFACE      = 0x01
USB_RECIP_ENDPOINT       = 0x02
USB_RECIP_OTHER          = 0x03

# bRequest
RQ_GET_STATUS            = 0x00
RQ_CLEAR_FEATURE         = 0x01
# Reserved for future use= 0x02
RQ_SET_FEATURE           = 0x03
# Reserved for future use= 0x04
RQ_SET_ADDRESS           = 0x05
RQ_GET_DESCRIPTOR        = 0x06
RQ_SET_DESCRIPTOR        = 0x07
RQ_GET_CONFIGURATION     = 0x08
RQ_SET_CONFIGURATION     = 0x09
RQ_GET_INTERFACE         = 0x0A
RQ_SET_INTERFACE         = 0x0B
RQ_SYNCH_FRAME           = 0x0C

RQ_VAR_READ              = 0x11
RQ_VAR_WRITE             = 0x12


class USBDeviceCustom(object):
    """
    USB device custom class.

    """

    def __init__(self):
        """
        Initialization of the class.

        """
        self.VENDOR_ID = 0x16C0  # Vendor ID (see V-USB)
        self.PRODUCT_ID = 0x05DC  # Product ID (see V-USB)
        self.Manufacturer = "baranovskiykonstantin@gmail.com"
        self.Product = "SDKT tool"
        self.timeout = 100
        self.handle = None
        self.device = None
        self.config = 1
        self.interface = 0
        self.deviceVersion = None
        self.dataLen = 2  # Lenght of the data block

    def find(self):
        """
        Find USB device by VENDOR_ID, PRODUCT_ID, Manufacturer, Product.

        """
        buses = usb.busses()
        for bus in buses :
            for device in bus.devices :
                if device.idVendor == self.VENDOR_ID and device.idProduct == self.PRODUCT_ID:
                    if (device.open().getString(2,len(self.Product)) == self.Product and
                        device.open().getString(1,len(self.Manufacturer)) == self.Manufacturer):
                        self.device = device
                        self.deviceVersion = device.deviceVersion
                        return True
        else:
            return False

    def open(self) :
        """
        Open device for exchanging data.

        """
        self.handle = self.device.open()
        self.handle.setConfiguration(self.config)
        self.handle.claimInterface(self.interface)
        self.handle.setAltInterface(self.interface)

    def close(self):
        """
        Close USB device.

        """
        try:
            self.handle.reset()
            self.handle.releaseInterface()
        except Exception, err:
            self.handle, self.device = None, None

    def setControlMsg(self, target, value):
        """
        Transmit data to the USB device through the control message.

            Arguments:

            target - id of the object (wIndex);

            value - data (wValue).

        """
        self.handle.controlMsg( USB_TYPE_VENDOR | USB_RECIP_DEVICE | USB_ENDPOINT_OUT, RQ_VAR_WRITE, None, value, target, self.timeout)

    def getControlMsg(self, target):
        """
         Get data from a USB device via a control message.

            Arguments:

            target - id of the object (wIndex).

        """
        self.answer = self.handle.controlMsg( USB_TYPE_VENDOR | USB_RECIP_DEVICE | USB_ENDPOINT_IN, RQ_VAR_READ, self.dataLen, 0, target,self.timeout)
        return self.answer[1] * 256 + self.answer[0]
