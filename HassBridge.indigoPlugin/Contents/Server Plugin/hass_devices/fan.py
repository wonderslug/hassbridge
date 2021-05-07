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
import math

import indigo
from hassbridge import TOPIC_ROOT, get_mqtt_client

from .base import BaseCommandableHADevice


class Fan(BaseCommandableHADevice):
    DEFAULT_STATE_TOPIC = TOPIC_ROOT + "/fan/status"
    COMMAND_TOPIC_TEMPLATE = TOPIC_ROOT + "/fan/switch"

    def __init__(self, indigo_entity, overrides, logger, discovery_prefix):
        super(Fan, self).__init__(indigo_entity, overrides, logger,
                                  discovery_prefix)
        self.config.update({
            self.PERCENTAGE_COMMAND_TOPIC_KEY: self.percentage_command_topic,
            self.PERCENTAGE_STATE_TOPIC_KEY: self.percentage_state_topic,
            self.SPEED_RANGE_MIN_KEY: self.speed_range_min,
            self.SPEED_RANGE_MAX_KEY: self.speed_range_max
        })

    @property
    def hass_type(self):
        return "fan"

    SPEED_RANGE_MIN_KEY = "speed_range_min"

    @property
    def speed_range_min(self):
        return 1

    SPEED_RANGE_MAX_KEY = "speed_range_max"

    @property
    def speed_range_max(self):
        return 3

    PERCENTAGE_STATE_TOPIC_TEMPLATE = TOPIC_ROOT + "/speed/percentage_state"
    PERCENTAGE_STATE_TOPIC_KEY = "percentage_state_topic"

    @property
    def percentage_state_topic(self):
        return self._overrideable_get(
            self.PERCENTAGE_STATE_TOPIC_KEY,
            self.PERCENTAGE_STATE_TOPIC_TEMPLATE).format(d=self)

    PERCENTAGE_COMMAND_TOPIC_TEMPLATE = TOPIC_ROOT + "/speed/percentage_command"
    PERCENTAGE_COMMAND_TOPIC_KEY = "percentage_command_topic"

    PERCENTAGE_STATE_TOPIC_RETAIN_KEY = "percentage_state_topic_retain"
    DEFAULT_PERCENTAGE_STATE_TOPIC_RETAIN = True

    @property
    def percentage_state_topic_retain(self):
        return bool(self._overrideable_get(
            self.PERCENTAGE_STATE_TOPIC_RETAIN_KEY,
            self.DEFAULT_PERCENTAGE_STATE_TOPIC_RETAIN))

    @property
    def percentage_command_topic(self):
        return self._overrideable_get(
            self.PERCENTAGE_COMMAND_TOPIC_KEY,
            self.PERCENTAGE_COMMAND_TOPIC_TEMPLATE).format(d=self)

    def register(self):
        super(Fan, self).register()

        # register brightness command topic
        self.logger.debug(
            u"Subscribing {} with id {}:{} to speed command topic {}"
            .format(self.hass_type, self.name, self.id,
                    self.percentage_command_topic))
        get_mqtt_client().message_callback_add(
            self.percentage_command_topic,
            self.on_percentage_command_message)
        get_mqtt_client().subscribe(self.percentage_command_topic)
        self.__send_percentage_state(self.indigo_entity)

    # pylint: disable=unused-argument
    def on_percentage_command_message(self, client, userdata, msg):
        indigo.speedcontrol.setSpeedIndex(
            self.id,
            value=int(msg.payload))

    def update(self, orig_dev, new_dev):
        super(Fan, self).update(orig_dev, new_dev)
        self.__send_percentage_state(new_dev)

    def __send_percentage_state(self, dev):
        get_mqtt_client().publish(
            topic=self.percentage_state_topic,
            payload=unicode(dev.speedIndex),
            retain=self.percentage_state_topic_retain)

    def cleanup(self):
        self.logger.debug(
            u'Cleaning up percentage_state_topic mqtt topics for device '
            u'{d[name]}:{d[id]} on topic {d[speed_state_topic]}'.format(d=self))
        get_mqtt_client().publish(
            topic=self.percentage_state_topic,
            payload='',
            retain=False)
        super(Fan, self).cleanup()
