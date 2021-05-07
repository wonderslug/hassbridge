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

import json
import re

import indigo
import pytz
import tzlocal
from hassbridge import (
    MQTT_UNIQUE_ID_TEMPLATE, RegisterableDevice, TOPIC_ROOT, UpdatableDevice,
    str2bool, get_mqtt_client)


class Base(object):
    MAIN_CONFIG_SECTION = 'root'
    CONFIG_VARS_SECTION = "config_vars"
    CONFIG_NAME = "name"

    def __init__(self, indigo_entity, overrides, logger):
        self._indigo_entity_id = indigo_entity.id
        self.id = indigo_entity.id
        self.overrides = overrides
        self.logger = logger
        self.ha_friendly_name = self.name
        self.track_updates_from = [str(indigo_entity.id)]
        self.attributes = []

    def is_following(self, indigo_id):
        if indigo_id in self.track_updates_from:
            return True
        return False

    def __getitem__(self, key):
        return getattr(self, key)

    def _overrideable_get(self, key, default, section=CONFIG_VARS_SECTION):
        ret = None
        if default is not None:
            ret = unicode(default).format(d=self)

        if section is self.MAIN_CONFIG_SECTION \
                and key in self.overrides \
                and self.overrides[key]:
            ret = unicode(self.overrides[key]).format(d=self)
        elif section in self.overrides \
                and key in self.overrides[section] \
                and self.overrides[section][key]:
            ret = unicode(self.overrides[section][key]).format(d=self)
        return ret

    @property
    def indigo_entity(self):
        if int(self._indigo_entity_id) not in indigo.devices:
            return None
        return indigo.devices[int(self._indigo_entity_id)]

    @property
    def name(self):
        return self._overrideable_get(self.CONFIG_NAME,
                                      self.indigo_entity.name).format(d=self)


class BaseHAEntity(Base, RegisterableDevice):
    """ Provides the basic Home Assistant MQTT Discovery Support """
    CONFIG_TOPIC_KEY = "config_topic"
    CONFIG_TOPIC_QOS_KEY = "config_topic_qos"
    CONFIG_TOPIC_RETAIN_KEY = "config_topic_retain"

    DEFAULT_CONFIG_TOPIC = TOPIC_ROOT + "/config"
    DEFAULT_CONFIG_TOPIC_QOS = 0
    DEFAULT_CONFIG_TOPIC_RETAIN = True

    CONFIG_UNIQUE_ID = "unique_id"
    CONFIG_QOS = "qos"

    def __init__(self, indigo_entity, overrides, logger,
                 discovery_prefix):
        super(BaseHAEntity, self).__init__(indigo_entity, overrides, logger)
        self.config_template = None
        self.ha_entity_id = None
        self.discovery_prefix = discovery_prefix
        self.config = {
            self.CONFIG_NAME: self.name,
            self.CONFIG_UNIQUE_ID: self.unique_id,
            self.CONFIG_QOS: self.qos
        }

    @property
    def _valid_string_config(self):
        return [self.CONFIG_NAME, self.CONFIG_UNIQUE_ID]

    @property
    def _valid_number_config(self):
        return [self.CONFIG_QOS]

    @property
    def _valid_boolean_config(self):
        return []

    @property
    def mqtt_name(self):
        name = self._overrideable_get(self.CONFIG_NAME, self.name).format(
            d=self).lower()
        name = re.sub(r"[^\w\s]", '', name)
        name = re.sub(r"\s+", '_', name)
        return name

    @property
    def unique_id(self):
        return self._overrideable_get(self.CONFIG_UNIQUE_ID,
                                      MQTT_UNIQUE_ID_TEMPLATE).format(d=self)

    @property
    def qos(self):
        return int(self._overrideable_get(
            self.CONFIG_QOS,
            self.DEFAULT_CONFIG_TOPIC_QOS).format(d=self))

    @property
    def config_topic(self):
        return self._overrideable_get(self.CONFIG_TOPIC_KEY,
                                      self.DEFAULT_CONFIG_TOPIC).format(d=self)

    @property
    def config_topic_qos(self):
        return int(self._overrideable_get(self.CONFIG_TOPIC_QOS_KEY,
                                          self.DEFAULT_CONFIG_TOPIC_QOS))

    @property
    def config_topic_retain(self):
        return bool(self._overrideable_get(self.CONFIG_TOPIC_RETAIN_KEY,
                                           self.DEFAULT_CONFIG_TOPIC_RETAIN))

    def register(self):
        self.logger.debug(
            u'Sending config for {d[name]}:{d[id]} '
            u'to topic {d[config_topic]}'.format(d=self))
        get_mqtt_client().publish(
            topic=self.config_topic,
            payload=json.dumps(self.config),
            qos=self.config_topic_qos,
            retain=self.config_topic_retain)

    def cleanup(self):
        self.logger.debug(
            u'Cleaning up config mqtt topics for device '
            u'{d[name]}:{d[id]} on topic {d[config_topic]}'
            .format(d=self))
        get_mqtt_client().publish(
            topic=self.config_topic,
            payload='',
            qos=self.config_topic_qos,
            retain=self.config_topic_retain)

    def shutdown(self):
        pass

    # Does this HA device get updates for the passed indigo device id
    def is_following(self, indigo_id):
        if indigo_id in self.track_updates_from:
            return True
        return False

    # @staticmethod
    # def device_diff(first, second):
    #     """ Return a dict of keys that differ with another config object.  If a value is
    #             not found in one fo the configs, it will be represented by KEYNOTFOUND.
    #         @param first:    Fist dictionary to diff.
    #         @param second:  Second dictionary to diff.
    #         @return diff:    Dict of Key => (first.val, second.val)
    #     """
    #     diff = {k: second[k] for k, _ in set(second.items()) - set(first.items())}
    #     return diff


class BaseAvailableHAEntity(BaseHAEntity):
    """ Adds Availability to the Home Assistance Discovery Devices """
    AVAILABILITY_TOPIC_QOS_KEY = "availability_topic_qos"
    AVAILABILITY_TOPIC_RETAIN_KEY = "availability_topic_retain"
    AVAILABILITY_TOPIC_TEMPLATE = TOPIC_ROOT + "/status"

    DEFAULT_AVAILABILITY_TOPIC_QOS = 0
    DEFAULT_AVAILABILITY_TOPIC_RETAIN = True

    DEFAULT_PAYLOAD_AVAILABLE = "online"
    DEFAULT_PAYLOAD_NOT_AVAILABLE = "offline"

    CONFIG_AVAILABILITY_TOPIC = "availability_topic"
    CONFIG_PAYLOAD_AVAILABLE = "payload_available"
    CONFIG_PAYLOAD_NOT_AVAILALE = "payload_not_available"

    def __init__(self, indigo_entity, overrides, logger,
                 discovery_prefix):
        super(BaseAvailableHAEntity, self).__init__(indigo_entity,
                                                    overrides,
                                                    logger,
                                                    discovery_prefix)
        self.config.update({
            "availability": [{
                "topic": self.availability_topic,
                self.CONFIG_PAYLOAD_AVAILABLE: self.payload_available,
                self.CONFIG_PAYLOAD_NOT_AVAILALE: self.payload_not_available
            }]
        })

    @property
    def _valid_string_config(self):
        return super(BaseAvailableHAEntity, self)._valid_string_config + [
            self.CONFIG_AVAILABILITY_TOPIC,
            self.CONFIG_PAYLOAD_AVAILABLE,
            self.CONFIG_PAYLOAD_NOT_AVAILALE
        ]

    def register(self):
        super(BaseAvailableHAEntity, self).register()
        get_mqtt_client().will_set(
            topic=self.availability_topic,
            payload=self.payload_not_available)
        self.logger.debug(u'Sending availability of {} for {} to {}'
                          .format(self.payload_available,
                                  self.name,
                                  self.availability_topic))
        get_mqtt_client().publish(
            topic=self.availability_topic,
            payload=self.payload_available,
            qos=self.availability_topic_qos,
            retain=self.availability_topic_retain)

    def cleanup(self):
        self.logger.debug(
            u'Cleaning up availability mqtt topics for device '
            u'{d[name]}:{d[id]} on topic {d[availability_topic]}'
            .format(d=self))
        get_mqtt_client().publish(
            topic=self.availability_topic,
            payload='',
            qos=self.availability_topic_qos,
            retain=self.availability_topic_retain)
        super(BaseAvailableHAEntity, self).cleanup()

    @property
    def availability_topic(self):
        return self._overrideable_get(
            self.CONFIG_AVAILABILITY_TOPIC,
            self.AVAILABILITY_TOPIC_TEMPLATE).format(d=self)

    @property
    def availability_topic_qos(self):
        return int(self._overrideable_get(
            self.AVAILABILITY_TOPIC_QOS_KEY,
            self.DEFAULT_AVAILABILITY_TOPIC_QOS))

    @property
    def availability_topic_retain(self):
        return bool(
            self._overrideable_get(
                self.AVAILABILITY_TOPIC_RETAIN_KEY,
                self.DEFAULT_AVAILABILITY_TOPIC_RETAIN))

    @property
    def payload_available(self):
        return self._overrideable_get(
            self.CONFIG_PAYLOAD_AVAILABLE,
            self.DEFAULT_PAYLOAD_AVAILABLE).format(d=self)

    @property
    def payload_not_available(self):
        return self._overrideable_get(
            self.CONFIG_PAYLOAD_NOT_AVAILALE,
            self.DEFAULT_PAYLOAD_NOT_AVAILABLE).format(d=self)

    def shutdown(self):
        get_mqtt_client().publish(
            topic=self.availability_topic,
            payload=self.payload_not_available,
            qos=self.availability_topic_qos,
            retain=self.availability_topic_retain)
        super(BaseAvailableHAEntity, self).shutdown()


class BaseStatefulHAEntity(BaseAvailableHAEntity):
    """ Adds basic stateful topics for a MQTT Discovered Entry """

    def __init__(self, indigo_entity, overrides, logger,
                 discovery_prefix):
        super(BaseStatefulHAEntity, self).__init__(indigo_entity, overrides,
                                                   logger, discovery_prefix)
        self.config.update({
            self.STATE_TOPIC_KEY: self._overrideable_get(self.STATE_TOPIC_KEY,
                                                         self.state_topic)
        })

    STATE_TOPIC_KEY = "state_topic"
    DEFAULT_STATE_TOPIC = TOPIC_ROOT + "/state"

    @property
    def state_topic(self):
        return self._overrideable_get(
            self.STATE_TOPIC_KEY,
            self.DEFAULT_STATE_TOPIC).format(d=self)

    STATE_TOPIC_QOS_KEY = "state_topic_qos"
    DEFAULT_STATE_TOPIC_QOS = 0

    @property
    def state_topic_qos(self):
        return int(
            self._overrideable_get(
                self.STATE_TOPIC_QOS_KEY,
                self.DEFAULT_STATE_TOPIC_QOS))

    STATE_TOPIC_RETAIN_KEY = "state_topic_retain"
    DEFAULT_STATE_TOPIC_RETAIN = True

    @property
    def state_topic_retain(self):
        return bool(
            self._overrideable_get(
                self.STATE_TOPIC_RETAIN_KEY,
                self.DEFAULT_STATE_TOPIC_RETAIN))

    def cleanup(self):
        self.logger.debug(
            u'Cleaning up state mqtt topics for device {d[name]}:{d[id]}'
            u' on topic {d[state_topic]}'
            .format(d=self))
        get_mqtt_client().publish(topic=self.state_topic,
                                  payload='',
                                  qos=self.state_topic_qos,
                                  retain=self.state_topic_retain)
        super(BaseStatefulHAEntity, self).cleanup()


class BaseStatefulHADevice(BaseStatefulHAEntity, UpdatableDevice):
    """ Provides the payload and attribute support for a Statful DEVICE """

    def __init__(self, indigo_entity, overrides, logger,
                 discovery_prefix):
        super(BaseStatefulHADevice, self).__init__(
            indigo_entity, overrides,
            logger, discovery_prefix)
        self.config.update({
            self.PAYLOAD_OFF_KEY: self._overrideable_get(
                self.PAYLOAD_OFF_KEY,
                self.payload_off),
            self.PAYLOAD_ON_KEY: self._overrideable_get(
                self.PAYLOAD_ON_KEY,
                self.payload_on),
            self.JSON_ATTRIBUTES_TOPIC_KEY: self.json_attribute_topic,
            'device': {
                'identifiers': [indigo_entity.address, indigo_entity.id],
                'manufacturer': u'{} via Indigo MQTT Bridge'.format(
                    indigo_entity.protocol),
                'model': indigo_entity.model,
                'name': indigo_entity.name,
                'connections': [
                    ['insteon', indigo_entity.address],
                    ['indigo', indigo_entity.id],

                ]
            }
        })

    PAYLOAD_ON_KEY = "payload_on"
    DEFAULT_PAYLOAD_ON = "ON"

    @property
    def payload_on(self):
        return self._overrideable_get(self.PAYLOAD_ON_KEY,
                                      self.DEFAULT_PAYLOAD_ON).format(d=self)

    PAYLOAD_OFF_KEY = "payload_off"
    DEFAULT_PAYLOAD_OFF = "OFF"

    @property
    def payload_off(self):
        return self._overrideable_get(self.PAYLOAD_OFF_KEY,
                                      self.DEFAULT_PAYLOAD_OFF).format(d=self)

    JSON_ATTRIBUTES_TOPIC_KEY = 'json_attributes_topic'
    JSON_ATTRIBUTES_TOPIC_TEMPLATE = TOPIC_ROOT + "/attributes"

    @property
    def json_attribute_topic(self):
        return self._overrideable_get(
            self.JSON_ATTRIBUTES_TOPIC_KEY,
            self.JSON_ATTRIBUTES_TOPIC_TEMPLATE).format(d=self)

    DEFAULT_JSON_ATTRIBUTES_TOPIC_QOS = 0
    JSON_ATTRIBUTES_TOPIC_QOS_KEY = 'json_attributes_topic_qos'

    @property
    def json_attribute_topic_qos(self):
        return int(
            self._overrideable_get(
                self.JSON_ATTRIBUTES_TOPIC_QOS_KEY,
                self.DEFAULT_JSON_ATTRIBUTES_TOPIC_QOS))

    DEFAULT_JSON_ATTRIBUTES_TOPIC_RETAIN = True
    JSON_ATTRIBUTES_TOPIC_RETAIN_KEY = 'json_attributes_topic_retain'

    @property
    def json_attribute_topic_retain(self):
        return bool(
            self._overrideable_get(
                self.JSON_ATTRIBUTES_TOPIC_RETAIN_KEY,
                self.DEFAULT_JSON_ATTRIBUTES_TOPIC_RETAIN))

    def register(self):
        super(BaseStatefulHADevice, self).register()
        self._send_state(self.indigo_entity)
        self._send_attributes(self.indigo_entity)

    # pylint: disable=unused-argument
    def update(self, orig_dev, new_dev):
        self._send_state(new_dev)
        self._send_attributes(new_dev)

    def _send_state(self, dev):
        state = self.payload_on if dev.onState else self.payload_off
        get_mqtt_client().publish(
            topic=self.state_topic,
            payload=state,
            qos=self.state_topic_qos,
            retain=self.state_topic_retain)

    def _send_attributes(self, dev):
        attributes = {
            'last_changed': dev.lastChanged.replace(
                tzinfo=tzlocal.get_localzone()
            ).astimezone(pytz.utc).strftime('%Y-%m-%dT%H:%M:%S.%f%z'),
            'last_successful_com': dev.lastSuccessfulComm.replace(
                tzinfo=tzlocal.get_localzone()
            ).astimezone(pytz.utc).strftime('%Y-%m-%dT%H:%M:%S.%f%z'),
            'indigo_id': self.id,
        }

        get_mqtt_client().publish(
            topic=self.json_attribute_topic,
            payload=json.dumps(attributes),
            qos=self.json_attribute_topic_qos,
            retain=self.json_attribute_topic_retain)

    def cleanup(self):
        self.logger.debug(
            u'Cleaning up json_attribute_topic mqtt topics for device '
            u'{d[name]}:{d[id]} on topic {d[json_attribute_topic]}'
            .format(d=self))
        get_mqtt_client().publish(
            topic=self.json_attribute_topic,
            payload='',
            qos=self.json_attribute_topic_qos,
            retain=False)
        super(BaseStatefulHADevice, self).cleanup()


class BaseCommandableHADevice(BaseStatefulHADevice):

    def __init__(self, indigo_entity, overrides, logger,
                 discovery_prefix):
        super(BaseCommandableHADevice, self).__init__(
            indigo_entity, overrides, logger, discovery_prefix)
        self.config.update({
            self.COMMAND_TOPIC_KEY: self.command_topic,
            self.OPTIMISTIC_KEY: self.optimistic
        })

    COMMAND_TOPIC_TEMPLATE = TOPIC_ROOT + "/set"
    COMMAND_TOPIC_KEY = "command_topic"

    @property
    def command_topic(self):
        return self._overrideable_get(
            self.COMMAND_TOPIC_KEY,
            self.COMMAND_TOPIC_TEMPLATE).format(d=self)

    OPTIMISTIC_KEY = "optimistic"
    DEFAULT_OPTIMISTIC = False

    @property
    def optimistic(self):
        retval = self._overrideable_get(
            self.OPTIMISTIC_KEY,
            self.DEFAULT_OPTIMISTIC)
        return str2bool(retval.format(d=self))

    def register(self):
        super(BaseCommandableHADevice, self).register()
        # register command topic
        self.logger.debug(
            u"Subscribing {} with id {}:{} to command topic {}"
            .format(self.hass_type, self.name, self.id, self.command_topic))
        get_mqtt_client().subscribe(self.command_topic)
        get_mqtt_client().message_callback_add(
            self.command_topic,
            self.on_command_message)

    # pylint: disable=unused-argument
    def on_command_message(self, client, userdata, msg):
        self.logger.debug(
            u"Command message {} recieved on {}".format(msg.payload,
                                                        msg.topic))
        if msg.payload == self.payload_on and \
                not indigo.devices[self.id].onState:
            indigo.device.turnOn(self.id)
        elif msg.payload == self.payload_off and \
                indigo.devices[self.id].onState:
            indigo.device.turnOff(self.id)

    def cleanup(self):
        self.logger.debug(
            u'Cleaning up command_topic mqtt topics for device "'
            u'{d[name]}:{d[id]} on topic {d[command_topic]}'
            .format(d=self))
        get_mqtt_client().publish(
            topic=self.command_topic,
            payload='',
            retain=False)
        super(BaseCommandableHADevice, self).cleanup()
