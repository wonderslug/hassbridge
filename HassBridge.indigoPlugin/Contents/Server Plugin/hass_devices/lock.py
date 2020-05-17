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
from hassbridge import get_mqtt_client


from .base import BaseCommandableHADevice


class Lock(BaseCommandableHADevice):

    def __init__(self, indigo_entity, overrides, logger,
                 discovery_prefix):
        super(Lock, self).__init__(
            indigo_entity, overrides,
            logger, discovery_prefix)
        if self.device_class is not None:
            self.config.update({self.DEVICE_CLASS_KEY: self.device_class})
        self.config.update({
            self.STATE_LOCKED_KEY: self.state_locked,
            self.STATE_UNLOCKED_KEY: self.state_unlocked,
            self.PAYLOAD_LOCK_KEY: self.payload_lock,
            self.PAYLOAD_UNLOCK_KEY: self.payload_unlock
        })
        del self.config[self.PAYLOAD_ON_KEY]
        del self.config[self.PAYLOAD_OFF_KEY]

    @property
    def hass_type(self):
        return "lock"

    DEVICE_CLASS_KEY = "device_class"
    DEFAULT_DEVICE_CLASS = None

    @property
    def device_class(self):
        ret = self._overrideable_get(
            self.DEVICE_CLASS_KEY,
            self.DEFAULT_DEVICE_CLASS)
        return ret.format(d=self) if ret is not None else ret

    STATE_LOCKED_KEY = "state_locked"
    DEFAULT_STATE_LOCKED = "LOCKED"

    @property
    def state_locked(self):
        return self._overrideable_get(
            self.STATE_LOCKED_KEY,
            self.DEFAULT_STATE_LOCKED).format(d=self)

    STATE_UNLOCKED_KEY = "state_unlocked"
    DEFAULT_STATE_UNLOCKED = "UNLOCKED"

    @property
    def state_unlocked(self):
        return self._overrideable_get(
            self.STATE_UNLOCKED_KEY,
            self.DEFAULT_STATE_UNLOCKED).format(d=self)

    PAYLOAD_LOCK_KEY = "payload_lock"
    DEFAULT_PAYLOAD_LOCK = "LOCK"

    @property
    def payload_lock(self):
        return self._overrideable_get(
            self.PAYLOAD_LOCK_KEY,
            self.DEFAULT_PAYLOAD_LOCK).format(d=self)

    PAYLOAD_UNLOCK_KEY = "payload_unlock"
    DEFAULT_PAYLOAD_UNLOCK = "UNLOCK"

    @property
    def payload_unlock(self):
        return self._overrideable_get(
            self.PAYLOAD_UNLOCK_KEY,
            self.DEFAULT_PAYLOAD_UNLOCK).format(d=self)

    def _send_state(self, dev):
        state = self.state_locked if dev.onState else self.state_unlocked
        self.logger.debug(
            u'Lock state set to {} for device {}'.format(state, dev.name))
        get_mqtt_client().publish(
            topic=self.state_topic,
            payload=state,
            qos=self.state_topic_qos,
            retain=self.state_topic_retain)

    def on_command_message(self, client, userdata, msg):
        self.logger.debug(
            u'Command message {} recieved on {}'
            .format(msg.payload, msg.topic))
        if msg.payload == self.payload_lock and \
                not indigo.devices[self.id].onState:
            indigo.device.turnOn(self.id)
        elif msg.payload == self.payload_unlock and \
                indigo.devices[self.id].onState:
            indigo.device.turnOff(self.id)
