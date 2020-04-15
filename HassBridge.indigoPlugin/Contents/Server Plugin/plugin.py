#! /usr/bin/env python
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

import imp
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.getcwd(), 'libs')))
sys.path.insert(0, os.path.abspath(os.getcwd()))
if __name__ == '__main__' and __package__ == None:
    imp.load_source('hassbridge',
                    os.path.normpath(os.path.join(os.getcwd(), '__init__.py')))
    imp.load_source('hassbridge.plugin',
                    os.path.normpath(os.path.join(os.getcwd(), 'plugin.py')))
    __package__ = "hassbridge"
    __name__ = "hassbridge.plugin"

# Note the "indigo" module is automatically imported and made available inside
# our global name space by the host process.

import indigo
import json
import paho.mqtt.client as mqtt
import requests

from hassbridge import (
    Config, CommandProcessor, UpdatableDevice,
    RegisterableDevice, TimedUpdateCheck, MqttClient)

from insteon import (
    InsteonDefaultTypesGenerator, InsteonKeypadTypesGenerator,
    InsteonInputOutputTypesGenerator, InsteonRemoteTypesGenerator,
    InsteonBatteryPoweredSensorsTypeGenerator)
from variables import VariableDefaultTypesGenerator
from virtual import VirtualDefaultTypesGenerator
from zwave import (
    ZWaveDefaultTypesGenerator,
    ZWaveBatteryPoweredSensorsTypeGenerator)


pVer = 0

mqtt_client = None

plugin_instance = None


class Plugin(indigo.PluginBase):
    ########################################
    # Main Functions
    ######################

    def __init__(self, plugin_id, display_name, version, prefs):
        indigo.PluginBase.__init__(self, plugin_id, display_name, version,
                                   prefs)
        pVer = version
        plugin_instance = self

        self.debug = prefs.get(u"showDebugInfo", False)
        if self.debug:
            self.logger.debug(u"Log debugging enabled")
        else:
            self.logger.debug(u"Log debugging disabled")

        self.config = Config(prefs, self.logger)

        # mqtt setup
        client = MqttClient.getInstance()

        self.mqtt_client = client.client = self._setup_mqtt_client()
        self.mqtt_client.on_connect = self.on_mqtt_connect
        self.mqtt_client.on_disconnect = self.on_mqtt_disconnect
        self.mqtt_client.on_message = self.on_mqtt_message
        self.mqtt_connected = False

        self._ha_devices = {}
        self._ha_device_followers = {}
        self._ha_device_address_mapping = {}
        self._started = False

    def __del__(self):
        indigo.PluginBase.__del__(self)

    def handle_exception(self, exc_type, exc_value, exc_traceback):
        self.logger.error(u'Exception trapped:' + unicode(exc_value))

    ####
    # Preferences Support
    ####

    def _setup_mqtt_client(self):
        client = mqtt.Client(
            client_id=self.config.mqtt_client_id,
            transport=self.config.mqtt_protocol)
        if self.config.mqtt_use_encryption:
            client.tls_set()
            if self.config.mqtt_allow_unvalidated:
                client.tls_insecure_set(True)
        return client

    def update_perfs(self, plugin_prefs):
        self.config = Config(plugin_prefs, self.logger)
        self._disconnect_from_mqtt_broker()
        client = MqttClient.getInstance()
        self.mqtt_client = client.client = self._setup_mqtt_client()
        self._connect_to_mqtt_broker()
        self._setup_ha_devices()
        self._register_ha_devices()

    def bridgable_devices_list_generator(self, filter="", valuesDict=None,
                                         typeId="", targetId=0):
        self.logger.debug(u"Getting list of Bridgable Devices")
        return_list = list()
        for dev in indigo.devices:
            if DeviceGeneratorFactory.is_bridgeable(dev, self.logger):
                return_list.append((str(dev.id), dev.name))
        return return_list

    ####
    # Plugin Overrides
    ####

    def closedPrefsConfigUi(self, values_dict, user_cancelled):
        if not user_cancelled:
            self.update_perfs(values_dict)

    def runConcurrentThread(self):
        self.logger.debug(u"Starting Concurrent Thread")
        while True:
            if self._started:
                if not self.mqtt_connected:
                    self._connect_to_mqtt_broker()
                self._refresh_ha_info()
                self._check_timed_updates()
            self.sleep(60)

    def deviceCreated(self, dev):
        self.logger.debug(u"Device Created")
        self._setup_ha_devices()
        self._register_ha_devices()

    def deviceUpdated(self, orig_dev, new_dev):
        indigo.PluginBase.deviceUpdated(self, orig_dev, new_dev)
        self._update_ha_device(orig_dev, new_dev)

    def deviceDeleted(self, dev):
        self._setup_ha_devices()
        self._register_ha_devices()

    def variableCreated(self, var):
        self._setup_ha_devices()
        self._register_ha_devices()

    def variableUpdated(self, orig_var, new_var):
        indigo.PluginBase.variableUpdated(self, orig_var, new_var)
        self._update_ha_device(orig_var, new_var)

    def variableDeleted(self, var):
        self._setup_ha_devices()
        self._register_ha_devices()

    def startup(self):
        self.logger.debug(u"startup called")

        # initial setup of ha devices
        self._setup_ha_devices()

        # initial connect to mqtt
        self._connect_to_mqtt_broker()

        # subscribe to indigo events
        indigo.devices.subscribeToChanges()
        indigo.variables.subscribeToChanges()

        self.logger.debug(u'subscribing to all INSTEON commands')
        if indigo.insteon.isEnabled():
            indigo.insteon.subscribeToIncoming()

        self._started = True

    def shutdown(self):
        self.logger.debug(u"shutdown called")
        self._disconnect_from_mqtt_broker()
        self._started = False

    def insteonCommandReceived(self, cmd):
        self.logger.debug(u'insteonCommandReceived: \n' + str(cmd))
        self._process_command(cmd)

    ####
    # MQTT Support
    ####
    def _connect_to_mqtt_broker(self):
        try:
            self._disconnect_from_mqtt_broker()
            self.logger.info(u"Connecting to the MQTT Server...")
            self.mqtt_client.username_pw_set(username=self.config.mqtt_username,
                                             password=self.config.mqtt_password)
            self.mqtt_client.connect(self.config.mqtt_server,
                                     self.config.mqtt_port, 59)
            self.logger.info(u"Connected to MQTT Server!")
            self.mqtt_client.loop_start()
        except Exception:
            t, v, tb = sys.exc_info()
            if v.errno == 61:
                self.logger.critical(
                    u"Connection Refused when connecting to broker.")
            elif v.errno == 60:
                self.logger.error(u"Timeout when connecting to broker.")
            else:
                self.handle_exception(t, v, tb)
                raise

    # The callback for when the client receives
    # a CONNACK response from the server.
    def on_mqtt_connect(self, client, userdata, flags, rc):
        try:
            self.logger.debug(
                u"Connected to MQTT server with result code " + unicode(rc))
            if rc == 0:
                self.mqtt_connected = True
                self._register_ha_devices()
            if rc == 1:
                indigo.server.self.logger(u"Error: Invalid Protocol Version.")
            if rc == 2:
                indigo.server.self.logger(u"Error: Invalid Client Identifier.")
            if rc == 3:
                indigo.server.self.logger(u"Error: Server Unavailable.")
            if rc == 4:
                indigo.server.self.logger(u"Error: Bad Username or Password.")
            if rc == 5:
                indigo.server.self.logger(u"Error: Not Authorised.")
        except Exception:
            t, v, tb = sys.exc_info()
            self.logger.debug({t, v, tb})
            self.handle_exception(t, v, tb)

    def _disconnect_from_mqtt_broker(self):
        if self.mqtt_connected:
            self.logger.debug(u"Disconnecting from MQTT Broker")
            for ha_device_id, ha_device in self._ha_devices.iteritems():
                if ha_device.indigo_entity is not None \
                        and isinstance(ha_device, RegisterableDevice):
                    ha_device.shutdown()
            self.mqtt_client.disconnect()
            self.mqtt_client.loop_stop()

    def on_mqtt_disconnect(self):
        self.logger.warn(u"Disconnected from MQTT Broker. ")
        self.mqtt_connected = False

    # The callback for when a PUBLISH message is received from the server.
    def on_mqtt_message(self, client, userdata, msg):
        try:
            self.logger.warn(
                u"Unhandled Message recd: " + msg.topic + " | " + unicode(
                    msg.payload))
        except Exception:
            t, v, tb = sys.exc_info()
            self.handle_exception(t, v, tb)

    ####
    # Update Handler Impl
    ####
    def _update_ha_device(self, orig, new):
        try:
            # call the base's implementation first just to make
            # sure all the right things happen elsewhere
            if str(new.id) in self._ha_device_followers:
                for ha_device in self._ha_device_followers[str(new.id)]:
                    if isinstance(ha_device, UpdatableDevice):
                        ha_device.update(orig, new)
        except Exception:
            t, v, tb = sys.exc_info()
            self.handle_exception(t, v, tb)
            raise

    def _check_timed_updates(self):
        for ha_device_id, ha_device in self._ha_devices.iteritems():
            if isinstance(ha_device, TimedUpdateCheck):
                ha_device.check_for_update()

    ####
    # Command Handler Impl
    ####
    def _process_command(self, cmd):
        # Handle Insteon Commands
        if isinstance(cmd,
                      indigo.InsteonCmd) and cmd.address in self._ha_device_address_mapping:
            device_map = self._ha_device_address_mapping[cmd.address]
            for ha_device in device_map:
                event = payload = None
                if isinstance(ha_device, CommandProcessor):
                    event, payload = ha_device.process_command(cmd, self.config)

                if event is not None:
                    self._send_event(event, payload)

    def _send_event(self, event, payload):
        try:
            self.logger.debug(u'Sending event {} to {} with payload {}'
                              .format(event, self.config.hass_url,
                                      json.dumps(payload)))
            url = '{}/api/events/{}'.format(self.config.hass_url, event)
            resp = self.config.hass_event_session.post(
                url,
                json=payload,
                verify=self.config.hass_ssl_validate)
            if resp.status_code is not requests.codes['OK']:
                self.logger.warn(
                    u'Unable to send event to home assitant, recieved {}'
                        .format(resp.text))
        except Exception as e:
            t, v, tb = sys.exc_info()
            self.handle_exception(t, v, tb)
            raise

    ####
    # Setup and MQTT Registration
    ####
    def _setup_ha_devices(self):
        self._remap_ha_devices()
        self._refresh_ha_info()

    def _remap_ha_devices(self):
        try:
            old_ha_devices = self._ha_devices
            new_device_followers_map = {}
            new_address_mapping = {}
            device_remove_list = []

            # Setup the list of devices
            for indigo_device in indigo.devices:
                if str(indigo_device.id) in self.pluginPrefs['devices']:

                    # Get the ha devices for each indigo device
                    hass_devices = DeviceGeneratorFactory.generate(
                        indigo_device, self.config, self.logger)

                    # Go through HA devices
                    for ha_device_id, ha_device in hass_devices.iteritems():
                        # setup the followers list
                        if str(
                                indigo_device.id) not in new_device_followers_map and ha_device.is_following(
                                str(indigo_device.id)):
                            new_device_followers_map[str(indigo_device.id)] = []
                        if ha_device.is_following(str(indigo_device.id)):
                            new_device_followers_map[
                                str(indigo_device.id)].append(ha_device)

                        # Set up the address to id map
                        if indigo_device.address:
                            if str(
                                    indigo_device.address) not in new_address_mapping:
                                new_address_mapping[
                                    str(indigo_device.address)] = []
                            new_address_mapping[
                                str(indigo_device.address)].append(ha_device)

                    self._ha_devices.update(hass_devices)

                # Find and remove unused ha devices
                if str(indigo_device.id) not in self.pluginPrefs[
                    'devices'] and str(indigo_device.id) in old_ha_devices:
                    self._unregister_ha_device(
                        old_ha_devices[str(indigo_device.id)])
                    device_remove_list.append(str(indigo_device.id))

            # Set up the list of variables
            for indigo_variable in indigo.variables:
                if str(indigo_variable.id) in self.pluginPrefs['variables']:

                    # Get the ha devices for each indigo variable
                    hass_devices = VariableGeneratorFactory.generate(
                        indigo_variable, self.config, self.mqtt_client,
                        self.logger)

                    # Go through HA devices
                    for ha_device_id, ha_device in hass_devices.iteritems():
                        # setup the followers list
                        if str(
                                indigo_variable.id) not in new_device_followers_map and ha_device.is_following(
                            str(indigo_variable.id)):
                            new_device_followers_map[
                                str(indigo_variable.id)] = []
                        if ha_device.is_following(str(indigo_variable.id)):
                            new_device_followers_map[
                                str(indigo_variable.id)].append(ha_device)

                    self._ha_devices.update(hass_devices)

                # Find and remove unused ha devices
                if str(indigo_variable.id) not in self.pluginPrefs[
                    'variables'] and str(indigo_variable.id) in old_ha_devices:
                    self._unregister_ha_device(
                        old_ha_devices[str(indigo_variable.id)])
                    device_remove_list.append(str(indigo_variable.id))

            # remove the references to old devices
            for remove_device in device_remove_list:
                old_ha_devices.pop(remove_device)

            self._ha_device_followers = new_device_followers_map
            self._ha_device_address_mapping = new_address_mapping

        except Exception as e:
            t, v, tb = sys.exc_info()
            self.handle_exception(t, v, tb)
            raise

    def _refresh_ha_info(self):
        try:
            self.logger.debug(
                u'Refreshing mappings of Indigo devices to HA devices.')
            url = '{}/api/states'.format(self.config.hass_url)

            headers = self.config.hass_session_headers
            headers['Content-Type'] = 'application/json'
            resp = requests.request('GET', url,
                                    verify=self.config.hass_ssl_validate,
                                    headers=headers)
            if resp.status_code is not requests.codes['OK']:
                self.logger.warn(
                    u'Unable to get mapping of indigo devices to home assitant entities, recieved {}'
                        .format(resp.text))

            ha_entities = resp.json()
            for ha_entity in ha_entities:
                if u'attributes' in ha_entity \
                        and u'indigo_id' in ha_entity[u'attributes'] \
                        and str(ha_entity[u'attributes'][u'indigo_id']) in self._ha_devices:
                    self._ha_devices[str(ha_entity[u'attributes'][u'indigo_id'])].ha_entity_id = \
                    ha_entity[u'entity_id']
                    self._ha_devices[str(ha_entity[u'attributes'][
                                             u'indigo_id'])].ha_friendly_name = \
                        ha_entity[u'attributes'][u'friendly_name']

        except Exception as e:
            t, v, tb = sys.exc_info()
            self.handle_exception(t, v, tb)
            raise

    def _register_ha_device(self, ha_device):
        if ha_device.indigo_entity is not None \
                and isinstance(ha_device, RegisterableDevice):
            ha_device.register()

    def _unregister_ha_device(self, ha_device):
        if ha_device.indigo_entity is not None \
                and isinstance(ha_device, RegisterableDevice):
            ha_device.cleanup()

    def _register_ha_devices(self):
        for ha_dev_id, ha_dev in self._ha_devices.iteritems():
            if ha_dev.indigo_entity is not None \
                    and ha_dev.indigo_entity.id in indigo.devices \
                    and isinstance(ha_dev, RegisterableDevice):
                ha_dev.register()


class DeviceGeneratorFactory(object):
    generators = [
        InsteonDefaultTypesGenerator,
        InsteonKeypadTypesGenerator,
        InsteonInputOutputTypesGenerator,
        InsteonRemoteTypesGenerator,
        InsteonBatteryPoweredSensorsTypeGenerator,
        ZWaveDefaultTypesGenerator,
        ZWaveBatteryPoweredSensorsTypeGenerator,
        VirtualDefaultTypesGenerator
    ]

    @staticmethod
    def generate(indigo_device, config, logger):
        devices = {}
        for generator in DeviceGeneratorFactory.generators:
            devices.update(
                generator.generate(indigo_device, config, logger))
            pass
        return devices

    @staticmethod
    def is_bridgeable(indigo_device, logger):
        for generator in DeviceGeneratorFactory.generators:
            if generator.is_bridgeable(indigo_device, logger):
                return True
        return False


class VariableGeneratorFactory(object):
    generators = [
        VariableDefaultTypesGenerator
    ]

    @staticmethod
    def generate(indigo_variable, config, logger):
        variables = {}
        for generator in VariableGeneratorFactory.generators:
            variables.update(
                generator.generate(indigo_variable, config, logger))
            pass
        return variables

    @staticmethod
    def is_bridgeable(indigo_variable, logger):
        for generator in VariableGeneratorFactory.generators:
            if generator.is_bridgeable(indigo_variable, logger):
                return True
        return False


def get_mqtt_client():
    client = MqttClient.getInstance()
    return client.client
