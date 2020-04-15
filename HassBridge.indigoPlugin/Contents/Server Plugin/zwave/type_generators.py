# -*- coding: utf-8 -*-

#  Copyright (c) 2020 Brian Towles
#
#  Permission is hereby granted, free of charge, to any person obtaining a copy
#  of this software and associated documentation files (the "Software"), to deal
#  in the Software without restriction, including without limitation the rights
#  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#  copies of the Software, and to permit persons to whom the Software is
#  furnished to do so, subject to the following conditions:
#
#  The above copyright notice and this permission notice shall be included in all
#  copies or substantial portions of the Software.
#
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
#  SOFTWARE.

import indigo

from .devices import (
    ZWaveBinarySensor, ZWaveFan, ZWaveLight, ZWaveSensor,
    ZWaveSwitch, ZWaveBatteryStateSensor)


class ZWaveDefaultTypesGenerator(object):

    @staticmethod
    def generate(dev, config, logger):
        devices = {}
        overrides = {}

        if u'zwave' != str(dev.protocol).lower():
            return devices

        bridge_type = ZWaveDefaultTypesGenerator._evaluate_device_type(
            dev,
            logger)
        if 'devices' in config.customizations and dev.name in \
                config.customizations['devices']:
            overrides = config.customizations['devices'][dev.name]
        if 'bridge_type' in overrides:
            bridge_type = overrides['bridge_type']
        if bridge_type and bridge_type in globals():
            hass_dev = globals()[bridge_type](dev, overrides, logger,
                                              config.hass_discovery_prefix)
            devices[str(dev.id)] = hass_dev
        return devices

    @staticmethod
    def _add_config_vars_device_class(overrides, device_class):
        if 'config_vars' not in overrides:
            overrides['config_vars'] = {}
        overrides['config_vars']['device_class'] = device_class

    @staticmethod
    def is_bridgeable(dev, logger):
        if u'zwave' != str(dev.protocol).lower():
            return False
        return True if ZWaveDefaultTypesGenerator._evaluate_device_type(
            dev,
            logger) is not None else False

    @staticmethod
    def _evaluate_device_type(dev, logger):
        bridge_type = None
        if type(dev) is indigo.SensorDevice:
            if not dev.supportsSensorValue:
                bridge_type = ZWaveBinarySensor.__name__
            else:
                bridge_type = ZWaveSensor.__name__
        elif type(dev) is indigo.RelayDevice:
            bridge_type = ZWaveSwitch.__name__
        elif type(dev) is indigo.DimmerDevice:
            bridge_type = ZWaveLight.__name__
        elif type(dev) is indigo.SpeedControlDevice:
            bridge_type = ZWaveFan.__name__
        return bridge_type


class ZWaveBatteryPoweredSensorsTypeGenerator(object):
    @staticmethod
    def generate(dev, config, logger):
        devices = {}
        if config.create_battery_sensors and dev.batteryLevel is not None:
            device = ZWaveBatteryStateSensor(dev, config.customizations, logger, config.hass_discovery_prefix)
            devices[device.id] = device
        return devices

    @staticmethod
    def is_bridgeable(dev, logger):
        return False
