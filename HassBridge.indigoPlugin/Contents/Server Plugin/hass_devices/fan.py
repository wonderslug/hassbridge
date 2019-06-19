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
from hassbridge import TOPIC_ROOT
import __main__

from .base import BaseCommandableHADevice


class Fan(BaseCommandableHADevice):
    DEFAULT_STATE_TOPIC = TOPIC_ROOT + "/fan/status"
    COMMAND_TOPIC_TEMPLATE = TOPIC_ROOT + "/fan/switch"

    def __init__(self, indigo_entity, overrides, logger,
            discovery_prefix):
        super(Fan, self).__init__(indigo_entity, overrides, logger,
            discovery_prefix)
        self.name_to_index = {"off": 0, "low": 1, "medium": 2, "high": 3}
        self.index_to_name = {0: "off", 1: "low", 2: "medium", 3: "high"}

        self.config.update({
            self.SPEED_COMMAND_TOPIC_KEY: self.speed_command_topic,
            self.SPEED_STATE_TOPIC_KEY: self.speed_state_topic,
            "payload_low_speed": "low",
            "payload_medium_speed": "medium",
            "payload_high_speed": "high",
            "speeds": ["off", "low", "medium", "high"]
        })

    @property
    def hass_type(self):
        return "fan"

    SPEED_COMMAND_TOPIC_TEMPLATE = TOPIC_ROOT + "/speed/set"
    SPEED_COMMAND_TOPIC_KEY = "speed_command_topic"

    @property
    def speed_command_topic(self):
        return self._overrideable_get(self.SPEED_COMMAND_TOPIC_KEY,
            self.SPEED_COMMAND_TOPIC_TEMPLATE).format(d=self)

    SPEED_STATE_TOPIC_TEMPLATE = TOPIC_ROOT + "/speed/status"
    SPEED_STATE_TOPIC_KEY = "speed_state_topic"

    @property
    def speed_state_topic(self):
        return self._overrideable_get(self.SPEED_STATE_TOPIC_KEY,
            self.SPEED_STATE_TOPIC_TEMPLATE).format(d=self)

    SPEED_STATE_TOPIC_RETAIN_KEY = "speed_state_topic_retain"
    DEFAULT_SPEED_STATE_TOPIC_RETAIN = True

    @property
    def speed_state_topic_retain(self):
        return bool(self._overrideable_get(self.SPEED_STATE_TOPIC_RETAIN_KEY,
            self.DEFAULT_SPEED_STATE_TOPIC_RETAIN))

    def register(self):
        super(Fan, self).register()

        # register brightness command topic
        self.logger.debug(
            "Subscribing {} with id {}:{} to speed command topic {}"
                .format(self.hass_type,
                self.name,
                self.id,
                self.speed_command_topic))
        __main__.get_mqtt_client().message_callback_add(self.speed_command_topic,
            self.on_speed_command_message)
        __main__.get_mqtt_client().subscribe(self.speed_command_topic)
        self.__send_speed_state(self.indigo_entity)

    def on_speed_command_message(self, client, userdata, msg):
        indigo.speedcontrol.setSpeedIndex(self.id,
            value=self.name_to_index[msg.payload])

    def update(self, orig_dev, new_dev):
        super(Fan, self).update(orig_dev, new_dev)
        self.__send_speed_state(new_dev)

    def __send_speed_state(self, dev):
        __main__.get_mqtt_client().publish(topic=self.speed_state_topic,
            payload=str(self.index_to_name[dev.speedIndex]),
            retain=self.speed_state_topic_retain)

    def cleanup(self):
        self.logger.debug(
            "Cleaning up speed_state_topic mqtt topics for device {d[name]}:{d[id]} on topic {d[speed_state_topic]}".format(
                d=self))
        __main__.get_mqtt_client().publish(topic=self.speed_state_topic,
            payload='',
            retain=False)
        super(Fan, self).cleanup()
