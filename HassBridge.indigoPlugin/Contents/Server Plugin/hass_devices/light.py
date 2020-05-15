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
from hassbridge import TOPIC_ROOT
import __main__

from .base import BaseCommandableHADevice


class Light(BaseCommandableHADevice):
    DEFAULT_STATE_TOPIC = TOPIC_ROOT + "/light/status"
    COMMAND_TOPIC_TEMPLATE = TOPIC_ROOT + "/light/switch"

    def __init__(self, indigo_entity, overrides, logger, discovery_prefix):
        super(Light, self).__init__(indigo_entity, overrides, logger, discovery_prefix)
        self._transition_from_dimmer = False
        self.config.update({
            self.BIRGHTNESS_STATE_TOPIC_KEY: self.brightness_state_topic,
            self.BRIGHTNESS_COMMAND_TOPIC_KEY: self.brightness_command_topic,
            self.BRIGHTNESS_SCALE_KEY: self.brightness_scale
        })
        if self.state_value_template is not None:
            self.config.update({self.STATE_VALUE_TEMPLATE_KEY: self.state_value_template})

    @property
    def hass_type(self):
        return "light"

    BRIGHTNESS_COMMAND_TOPIC_TEMPLATE = TOPIC_ROOT + "/brightness/set"
    BRIGHTNESS_COMMAND_TOPIC_KEY = "brightness_command_topic"

    @property
    def brightness_command_topic(self):
        return self._overrideable_get(self.BRIGHTNESS_COMMAND_TOPIC_KEY, self.BRIGHTNESS_COMMAND_TOPIC_TEMPLATE).format(d=self)

    BRIGHTNESS_STATE_TOPIC_TEMPLATE = TOPIC_ROOT + "/brightness/status"
    BIRGHTNESS_STATE_TOPIC_KEY = "brightness_state_topic"

    @property
    def brightness_state_topic(self):
        return self._overrideable_get(self.BIRGHTNESS_STATE_TOPIC_KEY, self.BRIGHTNESS_STATE_TOPIC_TEMPLATE).format(d=self)

    BRIGHTNESS_COMMAND_TOPIC_RETAIN_KEY = "brightness_command_topic_retain"
    DEFAULT_RIGHTNESS_COMMAND_TOPIC_RETAIN = True

    @property
    def brightness_command_topic_retain(self):
        return bool(self._overrideable_get(self.BRIGHTNESS_COMMAND_TOPIC_RETAIN_KEY, self.DEFAULT_RIGHTNESS_COMMAND_TOPIC_RETAIN))

    BRIGHTNESS_SCALE_KEY = "brightness_scale"
    DEFAULT_BRIGHTNESS_SCALE = 100

    @property
    def brightness_scale(self):
        return int(self._overrideable_get(self.BRIGHTNESS_SCALE_KEY, self.DEFAULT_BRIGHTNESS_SCALE).format(d=self))

    STATE_VALUE_TEMPLATE_KEY = "state_value_template"
    DEFAULT_STATE_VALUE_TEMPLATE = None

    @property
    def state_value_template(self):
        retval = self._overrideable_get(self.STATE_VALUE_TEMPLATE_KEY, self.DEFAULT_STATE_VALUE_TEMPLATE)
        return retval.format(d=self) if retval is not None else None

    def register(self):
        super(Light, self).register()
        # register brightness command topic
        self.logger.debug(
            "Subscribing {} with id {}:{} to brightness command topic {}"
                .format(self.hass_type,
                        self.name,
                        self.id,
                        self.brightness_command_topic))
        __main__.get_mqtt_client().message_callback_add(self.brightness_command_topic,
                                              self.on_brightness_command_message)
        __main__.get_mqtt_client().subscribe(self.brightness_command_topic)
        self.__send_brightness_state(self.indigo_entity)

    def on_brightness_command_message(self, client, userdata, msg):
        self.logger.debug("Brightness Command message {} recieved on {}"
                          .format(msg.payload, msg.topic))

        if (int(msg.payload) and not indigo.devices[self.id].onState) or int(msg.payload) == 0:
            self._transition_from_dimmer = True

        indigo.dimmer.setBrightness(self.id,
                                    value=int(msg.payload))

    def on_command_message(self, client, userdata, msg):
        if self._transition_from_dimmer:
            self._transition_from_dimmer = False
            return
        super(Light, self).on_command_message(client, userdata, msg)

    def update(self, orig_dev, new_dev):
        super(Light, self).update(orig_dev, new_dev)
        self.__send_brightness_state(new_dev)

    def __send_brightness_state(self, dev):
        self.logger.debug("Sending brightness state of {} to {}"
                          .format(dev.brightness,
                                  self.brightness_state_topic))
        __main__.get_mqtt_client().publish(topic=self.brightness_state_topic,
                                 payload=unicode(dev.brightness),
                                 retain=self.brightness_command_topic_retain)

    def cleanup(self):
        self.logger.debug("Cleaning up brightness_state_topic mqtt topics for device {d[name]}:{d[id]} on topic {d[brightness_state_topic]}".format(d=self))
        __main__.get_mqtt_client().publish(topic=self.brightness_state_topic,
                                 payload='',
                                 retain=False)
        super(Light, self).cleanup()
