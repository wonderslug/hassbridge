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

from .command_processors import INSTEON_EVENTS
from .devices import InsteonKeypadButtonLight, \
    InsteonBinarySensor, InsteonFan, InsteonSwitch, \
    InsteonSensor, InsteonLight, InsteonCover, InsteonRemote, \
    InsteonBatteryStateSensor, InsteonButtonActivityTracker

INSTEON_KEYPAD_8_BUTTON_MAP = {2: 'B', 3: 'C', 4: 'D', 5: 'E', 6: 'F', 7: 'G', 8: 'H'}
INSTEON_KEYPAD_6_BUTTON_MAP = {3: 'A', 4: 'B', 5: 'C', 6: 'D'}

INSTEON_KEYPAD_MODELS = {
    u'KeypadLinc Dimmer (2334)': False,
    u'KeypadLinc Dimmer (2334-232)': False,
    u'KeypadLinc Relay': True,
}

INSTEON_8_BUTTON_REMOTE_MAP = {1: 'B', 2: 'A', 3: 'D', 4: 'C', 5: 'F', 6: 'E', 7: 'H', 8: 'G'}
INSTEON_4_BUTTON_REMOTE_MAP = {1: 'A', 2: 'B', 3: 'C', 4: 'D'}
INSTEON_1_BUTTON_REMOTE_MAP = {1: None}

INSTEON_REMOTE_MODELS = {
    u'RemoteLinc 2 4-Scene': INSTEON_4_BUTTON_REMOTE_MAP,
    u'RemoteLinc 2 8-Scene': INSTEON_8_BUTTON_REMOTE_MAP,
    u'RemoteLinc 2 Switch': INSTEON_1_BUTTON_REMOTE_MAP
}

HA_DEVICE_CLASS_MOISTURE = 'moisture'
HA_DEVICE_CLASS_DOOR = 'door'
HA_DEVICE_CLASS_WINDOW = 'window'
HA_DEVICE_CLASS_MOTION = 'motion'


class InsteonDefaultTypesGenerator(object):

    @staticmethod
    def generate(dev, config, logger):

        devices = {}
        overrides = {}
        if u'insteon' != str(dev.protocol).lower():
            return devices
        bridge_type = InsteonDefaultTypesGenerator._evaluate_device_type(dev, logger)
        if 'devices' in config.customizations and dev.name in config.customizations['devices']:
            overrides = config.customizations['devices'][dev.name]
        if 'bridge_type' in overrides:
            bridge_type = overrides['bridge_type']
        if bridge_type and bridge_type in globals():
            overrides = InsteonDefaultTypesGenerator._define_likley_device_class(dev, overrides)
            hass_dev = globals()[bridge_type](dev, overrides, logger, config.hass_discovery_prefix)
            devices[str(dev.id)] = hass_dev
        return devices

    @staticmethod
    def _define_likley_device_class(indigo_device, overrides):
        if 'config_vars' not in overrides or 'device_class' not in overrides['config_vars']:
            if str(indigo_device.model) == u'Leak Sensor':
                InsteonDefaultTypesGenerator._add_config_vars_device_class(overrides, HA_DEVICE_CLASS_MOISTURE)
            elif str(indigo_device.model) == u'Door Sensor':
                InsteonDefaultTypesGenerator._add_config_vars_device_class(overrides, HA_DEVICE_CLASS_DOOR)
            elif str(indigo_device.model) == u'Open/Close Sensor':
                if 'door' in indigo_device.name.lower():
                    InsteonDefaultTypesGenerator._add_config_vars_device_class(overrides, HA_DEVICE_CLASS_DOOR)
                elif 'window' in indigo_device.name.lower():
                    InsteonDefaultTypesGenerator._add_config_vars_device_class(overrides, HA_DEVICE_CLASS_WINDOW)
            elif str(indigo_device.model) == u'Motion Sensor (2844)' or 'motion' in indigo_device.name.lower():
                InsteonDefaultTypesGenerator._add_config_vars_device_class(overrides, HA_DEVICE_CLASS_MOTION)
        return overrides

    @staticmethod
    def _add_config_vars_device_class(overrides, device_class):
        if 'config_vars' not in overrides:
            overrides['config_vars'] = {}
        overrides['config_vars']['device_class'] = device_class

    @staticmethod
    def is_bridgeable(dev, logger):
        if u'insteon' != str(dev.protocol).lower():
            return False
        return True if InsteonDefaultTypesGenerator._evaluate_device_type(dev, logger) is not None else False

    @staticmethod
    def _evaluate_device_type(dev, logger):
        bridge_type = None
        # is_battery_powered = False
        if type(dev) is indigo.SensorDevice:
            if not dev.supportsSensorValue:
                bridge_type = InsteonBinarySensor.__name__
            else:
                bridge_type = InsteonSensor.__name__
            # if str(dev.model) in ['Leak Sensor', 'Open/Close Sensor', 'Door Sensor', 'Motion Sensor (2844)']:
            #     is_battery_powered = True
        elif type(dev) is indigo.RelayDevice:
            bridge_type = InsteonSwitch.__name__
        elif type(dev) is indigo.DimmerDevice:
            bridge_type = InsteonLight.__name__
        elif type(dev) is indigo.SpeedControlDevice:
            bridge_type = InsteonFan.__name__
        return bridge_type


class InsteonKeypadTypesGenerator(object):

    @staticmethod
    def generate(dev, config, logger):
        devices = {}
        overrides = {}
        if dev.model in INSTEON_KEYPAD_MODELS:
            if dev.buttonConfiguredCount == 6:
                button_map = INSTEON_KEYPAD_6_BUTTON_MAP
            else:
                button_map = INSTEON_KEYPAD_8_BUTTON_MAP

            for button_id, button_label in button_map.iteritems():
                device = InsteonKeypadButtonLight(dev, config.customizations, logger,
                                                  config.hass_discovery_prefix, button_id, button_label)
                device.is_relay = INSTEON_KEYPAD_MODELS[dev.model]
                devices[device.id] = device

                # Setup the device activty trackers for the buttons
                for event, activity_type in INSTEON_EVENTS.iteritems():
                    button_activity_device = InsteonButtonActivityTracker(dev,
                                                                          config.customizations,
                                                                          logger,
                                                                          config.hass_discovery_prefix,
                                                                          button_id,
                                                                          button_label,
                                                                          activity_type)
                    devices[button_activity_device.id] = button_activity_device
        return devices

    @staticmethod
    def is_bridgeable(dev, logger):
        return False


class InsteonInputOutputTypesGenerator(InsteonDefaultTypesGenerator):

    @staticmethod
    def generate(dev, config, logger):
        devices = {}
        overrides = {}
        bridge_type = InsteonInputOutputTypesGenerator._evaluate_device_type(dev, logger)
        if 'devices' in config.customizations and dev.name in config.customizations['devices']:
            overrides = config.customizations['devices'][dev.name]
        if 'bridge_type' in overrides:
            bridge_type = overrides['bridge_type']
        if bridge_type and bridge_type in globals():
            hass_dev = globals()[bridge_type](dev, overrides, logger, config.hass_discovery_prefix)
            devices[str(dev.id)] = hass_dev
        return devices

    @staticmethod
    def is_bridgeable(dev, logger):
        return True if InsteonInputOutputTypesGenerator._evaluate_device_type(dev, logger) is not None else False

    @staticmethod
    def _evaluate_device_type(dev, logger):
        bridge_type = None
        if type(dev) is indigo.MultiIODevice:
            bridge_type = InsteonCover.__name__
        return bridge_type


class InsteonRemoteTypesGenerator(object):

    @staticmethod
    def generate(dev, config, logger):
        devices = {}
        overrides = {}
        if 'devices' in config.customizations and dev.name in config.customizations['devices']:
            overrides = config.customizations['devices'][dev.name]

        if dev.model in INSTEON_REMOTE_MODELS:
            button_map = INSTEON_REMOTE_MODELS[dev.model]
            for button_id, button_label in button_map.iteritems():
                device = InsteonRemote(dev, overrides, logger, button_id, button_label)
                devices[device.id] = device

                # Setup the device activty trackers for the buttons
                for event, activity_type in INSTEON_EVENTS.iteritems():
                    button_activity_device = InsteonButtonActivityTracker(dev,
                                                                          config.customizations,
                                                                          logger,
                                                                          config.hass_discovery_prefix,
                                                                          button_id,
                                                                          button_label,
                                                                          activity_type)
                    devices[button_activity_device.id] = button_activity_device
        return devices

    @staticmethod
    def is_bridgeable(dev, logger):
        if dev.model in INSTEON_REMOTE_MODELS:
            return True
        return False


class InsteonBatteryPoweredSensorsTypeGenerator(object):
    @staticmethod
    def generate(dev, config, logger):
        devices = {}
        if config.create_battery_sensors and str(dev.model) in ['Leak Sensor', 'Open/Close Sensor', 'Door Sensor', 'Motion Sensor (2844)']:
            device = InsteonBatteryStateSensor(dev, config.customizations, logger, config.hass_discovery_prefix)
            devices[device.id] = device
        return devices

    @staticmethod
    def is_bridgeable(dev, logger):
        return False
