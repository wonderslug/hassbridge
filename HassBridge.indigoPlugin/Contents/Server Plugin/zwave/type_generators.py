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
#  The above copyright notice and this permission notice shall be included in
#  all copies or substantial portions of the Software.
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
    ZWaveBinarySensor, ZWaveFan, ZWaveLight, ZWaveLock, ZWaveSensor,
    ZWaveSwitch, ZWaveBatteryStateSensor)


class ZWaveDefaultTypesGenerator(object):

    @staticmethod
    def generate(dev, config, logger):
        devices = {}
        overrides = config.get_overrides_for_device(dev)

        if str(dev.protocol).lower() != u'zwave':
            return devices

        bridge_type = ZWaveDefaultTypesGenerator._evaluate_device_type(dev)
        if 'bridge_type' in overrides:
            bridge_type = overrides['bridge_type']
        if bridge_type and bridge_type in globals():
            logger.debug(u'Setting {} as bridge type {}'
                         .format(dev.name, bridge_type))
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
    def is_bridgeable(dev):
        if str(dev.protocol).lower() != u'zwave':
            return False
        return True if ZWaveDefaultTypesGenerator._evaluate_device_type(dev) \
                       is not None else False

    @staticmethod
    def _evaluate_device_type(dev):
        bridge_type = None
        if isinstance(dev, indigo.SensorDevice):
            if not dev.supportsSensorValue:
                bridge_type = ZWaveBinarySensor.__name__
            else:
                bridge_type = ZWaveSensor.__name__
        elif isinstance(dev, indigo.DimmerDevice):
            bridge_type = ZWaveLight.__name__
        elif isinstance(dev, indigo.SpeedControlDevice):
            bridge_type = ZWaveFan.__name__
        elif isinstance(dev, indigo.RelayDevice):
            if dev.ownerProps.get("IsLockSubType", False):
                bridge_type = ZWaveLock.__name__
            else:
                bridge_type = ZWaveSwitch.__name__
        return bridge_type


class ZWaveBatteryPoweredSensorsTypeGenerator(object):
    @staticmethod
    def generate(dev, config, logger):
        devices = {}
        overrides = config.get_overrides_for_device(dev)
        # pylint: disable=too-many-boolean-expressions
        if str(dev.protocol).lower() == u'zwave' and \
            dev.batteryLevel is not None and \
            (
                    (config.create_battery_sensors and
                     'enable_battery_sensor' not in overrides)
                    or
                    ('enable_battery_sensor' in overrides and
                     overrides['enable_battery_sensor'] is True)
            ):
            device = ZWaveBatteryStateSensor(dev,
                                             config.customizations,
                                             logger,
                                             config.hass_discovery_prefix)
            devices[device.id] = device
        return devices

    @staticmethod
    # pylint: disable=unused-argument
    def is_bridgeable(dev):
        return False
