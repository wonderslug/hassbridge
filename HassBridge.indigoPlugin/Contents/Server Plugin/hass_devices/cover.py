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
import __main__

from .base import BaseCommandableHADevice


class Cover(BaseCommandableHADevice):

    def __init__(self, indigo_entity, overrides, logger,
            discovery_prefix):
        super(Cover, self).__init__(indigo_entity, overrides,
            logger, discovery_prefix)
        if self.device_class is not None:
            self.config.update({self.DEVICE_CLASS_KEY: self.device_class})
        self.config.update({
            self.STATE_OPEN_KEY: self.state_open,
            self.STATE_CLOSED_KEY: self.state_closed,
            self.PAYLOAD_OPEN_KEY: self.payload_open,
            self.PAYLOAD_CLOSE_KEY: self.payload_close,
            self.PAYLOAD_STOP_KEY: self.payload_stop
        })
        del self.config[self.PAYLOAD_ON_KEY]
        del self.config[self.PAYLOAD_OFF_KEY]

    @property
    def hass_type(self):
        return "cover"

    DEVICE_CLASS_KEY = "device_class"
    DEFAULT_DEVICE_CLASS = None

    @property
    def device_class(self):
        ret = self._overrideable_get(self.DEVICE_CLASS_KEY,
            self.DEFAULT_DEVICE_CLASS)
        return ret.format(d=self) if ret is not None else ret

    STATE_OPEN_KEY = "state_open"
    DEFAULT_STATE_OPEN = "open"

    @property
    def state_open(self):
        return self._overrideable_get(self.STATE_OPEN_KEY,
            self.DEFAULT_STATE_OPEN).format(d=self)

    STATE_CLOSED_KEY = "state_closed"
    DEFAULT_STATE_CLOSED = "closed"

    @property
    def state_closed(self):
        return self._overrideable_get(self.STATE_CLOSED_KEY,
            self.DEFAULT_STATE_CLOSED).format(d=self)

    PAYLOAD_OPEN_KEY = "payload_open"
    DEFAULT_PAYLOAD_OPEN = "OPEN"

    @property
    def payload_open(self):
        return self._overrideable_get(self.PAYLOAD_OPEN_KEY,
            self.DEFAULT_PAYLOAD_OPEN).format(d=self)

    PAYLOAD_CLOSE_KEY = "payload_close"
    DEFAULT_PAYLOAD_CLOSE = "CLOSE"

    @property
    def payload_close(self):
        return self._overrideable_get(self.PAYLOAD_CLOSE_KEY,
            self.DEFAULT_PAYLOAD_CLOSE).format(d=self)

    PAYLOAD_STOP_KEY = "payload_stop"
    DEFAULT_PAYLOAD_STOP = "STOP"

    @property
    def payload_stop(self):
        return self._overrideable_get(self.PAYLOAD_STOP_KEY,
            self.DEFAULT_PAYLOAD_STOP).format(d=self)

    def _send_state(self, dev):
        state = self.state_open if not dev.binaryInputs[
            0] else self.state_closed
        self.logger.debug(
            "Cover State set to {} for device {}".format(state, dev.name))
        __main__.get_mqtt_client().publish(topic=self.state_topic,
            payload=state,
            qos=self.state_topic_qos,
            retain=self.state_topic_retain)

    def on_command_message(self, client, userdata, msg):
        self.logger.debug(
            "Command message {} recieved on {}".format(msg.payload, msg.topic))
        if msg.payload in [self.payload_open, self.payload_close,
            self.payload_stop]:
            indigo.iodevice.setBinaryOutput(self.id, index=0, value=True)
