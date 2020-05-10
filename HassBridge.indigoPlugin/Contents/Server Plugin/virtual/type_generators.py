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
import json

from .devices import VirtualSwitch, VirtualLight, VirtualBinarySensor

VIRTUAL_DEVICES_PLUGIN = \
    u'com.perceptiveautomation.indigoplugin.devicecollection'
VIRTUAL_DEVICES_PROTOCOL = u'plugin'


class VirtualDefaultTypesGenerator(object):

    @staticmethod
    def generate(dev, config, logger):
        devices = {}
        overrides = config.get_overrides_for_device(dev)

        if str(dev.protocol).lower() != VIRTUAL_DEVICES_PROTOCOL \
                and str(dev.pluginId).lower() != VIRTUAL_DEVICES_PLUGIN:
            return devices

        bridge_type = VirtualDefaultTypesGenerator._evaluate_device_type(
            dev,
            logger)
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
        if str(dev.protocol).lower() != VIRTUAL_DEVICES_PROTOCOL \
                or str(dev.pluginId).lower() != VIRTUAL_DEVICES_PLUGIN:
            return False

        return True if VirtualDefaultTypesGenerator._evaluate_device_type(
            dev,
            logger) is not None else False

    @staticmethod
    def _evaluate_device_type(dev, logger):
        bridge_type = None
        if type(dev) is indigo.RelayDevice:
            if dev.model == u'Device Group':
                device_list = json.loads(dev.ownerProps['deviceListDict'])
                if len(device_list['relays']) == 0 \
                        and len(device_list['dimmers']) == 0:
                    bridge_type = VirtualBinarySensor.__name__
                else:
                    bridge_type = VirtualSwitch.__name__
        return bridge_type
