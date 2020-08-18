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

import os
import sys

# pylint: disable=import-error
import jwt
from jwt.exceptions import InvalidTokenError
import requests
# pylint: disable=import-error
import yaml

DEFAULT_CONFIG_LOCATION = './config_templates'
EVENT_PREFIX_DEFAULT = u'indigo_hassbridge'
HASS_DISCOVERY_PREFIX_DEFAULT = u'homeassistant'
HASS_URL_DEFAULT = u'http://localhost:8123'

TOPIC_ROOT = u'{d[discovery_prefix]}/{d[hass_type]}/{d[mqtt_name]}'
MQTT_UNIQUE_ID_TEMPLATE = u'indigo_mqtt_{d[mqtt_name]}'


def str2bool(value):
    return value.lower() in (u"yes", u"true", u"t", u"1")


class Config(object):
    def __init__(self, pluginPrefs, logger):
        super(Config, self).__init__()
        self.logger = logger
        self.debug = pluginPrefs.get(u"showDebugInfo", False)
        self.mqtt_protocol = pluginPrefs.get(u"mqtt_protocol", u'tcp')
        self.mqtt_server = pluginPrefs.get(u"serverAddress", u'localhost')
        self.mqtt_port = int(pluginPrefs.get(u"serverPort", 1883))
        self.mqtt_username = pluginPrefs.get(u"serverUsername", u"")
        self.mqtt_password = pluginPrefs.get(u"serverPassword", u"")
        self.mqtt_use_encryption = pluginPrefs.get(
            u"mqtt_use_encryption",
            False)
        self.mqtt_allow_unvalidated = pluginPrefs.get(
            u"mqtt_allow_unvalidated",
            False)
        self.mqtt_set_client_id = pluginPrefs.get(u"mqtt_set_client_id", False)
        self.mqtt_client_id = pluginPrefs.get(u"mqtt_client_id", u"")
        if not self.mqtt_set_client_id:
            self.mqtt_client_id = u""

        self.hass_access_token = pluginPrefs.get(u'access_token', u'')
        try:
            jwt.decode(self.hass_access_token, verify=False)
        except InvalidTokenError:
            self.logger.warn(u'Access Token does not appear to be valid.')
        self.hass_session_headers = {
            'Authorization': 'Bearer {}'.format(self.hass_access_token)
        }
        self.hass_url = pluginPrefs.get(u'server_url', HASS_URL_DEFAULT)
        if self.hass_url.endswith('/'):
            self.hass_url = self.hass_url[:-1]

        self.hass_ssl_validate = pluginPrefs.get(
            u'https_validate_cert', True)
        self.hass_event_prefix = pluginPrefs.get(
            u'event_prefix',
            EVENT_PREFIX_DEFAULT)
        self.hass_discovery_prefix = pluginPrefs.get(
            u'discovery_prefix',
            HASS_DISCOVERY_PREFIX_DEFAULT)

        # Setup the events session
        self.hass_event_session = requests.Session()
        self.hass_event_session.headers = self.hass_session_headers

        self.customizations = {}
        self.use_customize_file = pluginPrefs.get(
            u"use_customization_file",
            False)
        self.customize_file_path = pluginPrefs.get(
            u"customization_file_path",
            u"")

        self.create_battery_sensors = pluginPrefs.get(
            u"create_battery_sensors",
            False)
        self.create_insteon_led_backlight_lights = pluginPrefs.get(
            u'create_insteon_led_backlight_lights',
            False
        )

        self.insteon_no_comm_minutes = int(pluginPrefs.get(
            u"insteon_battery_minutes_no_com", 1440))

        if self.use_customize_file:
            self.customizations = self.__read_customization_file()

    def __read_customization_file(self):
        customizations = {}
        try:

            if os.path.isfile(self.customize_file_path):
                stream = file(self.customize_file_path, 'r')
                customizations = yaml.full_load(stream)
                if customizations is None:
                    customizations = {}
            else:
                self.logger.error(u"Unable to find customization file {}"
                                  .format(self.customize_file_path))
            return customizations
        except Exception:
            execp_type, execpt_value, except_traceback = sys.exc_info()
            self.__handle_exception(execp_type, execpt_value, except_traceback)
            raise

    # pylint: disable=unused-argument
    def __handle_exception(self, exc_type, exc_value, exc_traceback):
        self.logger.error(u'Exception trapped:' + unicode(exc_value))

    def get_overrides_for_device(self, dev):
        overrides = {}
        if self.customizations is not None and \
                'devices' in self.customizations and \
                dev.name in self.customizations['devices']:
            overrides = self.customizations['devices'][dev.name]
        if overrides is None:
            overrides = {}
        return overrides


class RegisterableDevice(object):
    def register(self):
        pass

    def cleanup(self):
        pass

    def shutdown(self):
        pass


class UpdatableDevice(object):
    def update(self, orig_dev, new_dev):
        pass


class CommandProcessor(object):
    # pylint: disable=no-self-use, unused-argument
    def process_command(self, cmd, config):
        """Handles converting a command into an event and payload to pass to
        an EventSender
        """
        return None, None


class TimedUpdateCheck(object):
    def check_for_update(self):
        pass


def get_mqtt_client():
    client = MqttClient.get_instance()
    return client.client


class MqttClient(object):
    # Here will be the instance stored.
    __instance = None

    @staticmethod
    def get_instance():
        """ Static access method. """
        if MqttClient.__instance is None:
            MqttClient()
        return MqttClient.__instance

    def __init__(self):
        """ Virtually private constructor. """
        if MqttClient.__instance is not None:
            raise Exception("This class is a singleton!")
        else:
            MqttClient.__instance = self
        self.client = None
