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

import re
from datetime import datetime, timedelta

import indigo
import tzlocal
from hass_devices import Switch, Sensor, Fan, Light, BinarySensor, Cover
from hass_devices.base import Base, BaseHAEntity
from hassbridge import TimedUpdateCheck, TOPIC_ROOT
import __main__

from .command_processors import InsteonRemoteCommandProcessor, \
    InsteonKeypadButtonCommandProcessor, \
    InsteonGeneralCommandProcessor, \
    InsteonCommandProcessor, INSTEON_EVENTS


class InsteonBinarySensor(BinarySensor):
    def __init__(self, indigo_entity, overrides, logger, discovery_prefix):
        super(InsteonBinarySensor, self).__init__(indigo_entity, overrides, logger, discovery_prefix)


class InsteonSensor(Sensor):
    def __init__(self, indigo_entity, overrides, logger, discovery_prefix):
        super(InsteonSensor, self).__init__(indigo_entity, overrides, logger, discovery_prefix)


class InsteonSwitch(Switch, InsteonGeneralCommandProcessor):
    def __init__(self, indigo_entity, overrides, logger, discovery_prefix):
        super(InsteonSwitch, self).__init__(indigo_entity, overrides, logger, discovery_prefix)


class InsteonLight(Light, InsteonGeneralCommandProcessor):
    def __init__(self, indigo_entity, overrides, logger, discovery_prefix):
        super(InsteonLight, self).__init__(indigo_entity, overrides, logger, discovery_prefix)


class InsteonFan(Fan):
    def __init__(self, indigo_entity, overrides, logger, discovery_prefix):
        super(InsteonFan, self).__init__(indigo_entity, overrides, logger, discovery_prefix)


class InsteonCover(Cover):
    def __init__(self, indigo_entity, overrides, logger, discovery_prefix):
        super(InsteonCover, self).__init__(indigo_entity, overrides, logger, discovery_prefix)


class InsteonKeypadButtonLight(Switch, InsteonKeypadButtonCommandProcessor):
    def __init__(self, indigo_entity, overrides, logger, discovery_prefix, button, label):
        self.is_relay = False
        self.button = button
        self.label = label
        super(InsteonKeypadButtonLight, self).__init__(indigo_entity, overrides, logger, discovery_prefix)
        self.id = "{}_{}".format(indigo_entity.id, button)
        self.parent_id = indigo_entity.id

    @property
    def hass_type(self):
        return "light"

    @property
    def name(self):
        return self._overrideable_get(self.CONFIG_NAME, self.indigo_entity.name + " Button {}".format(self.label)).format(d=self)

    @property
    def mqtt_name(self):
        name = self._overrideable_get(self.CONFIG_NAME, self.indigo_entity.name + " Button {}".format(self.label)).format(d=self).lower()
        name = re.sub(r"[^\w\s]", '', name)
        name = re.sub(r"\s+", '_', name)
        return name

    def update(self, orig_dev, new_dev):
        self._send_state(new_dev)

    def _send_state(self, dev):
        state = self.payload_on if dev.ledStates[self.button - 1] else self.payload_off
        __main__.get_mqtt_client().publish(topic=self.state_topic,
                                 payload=state,
                                 qos=self.state_topic_qos,
                                 retain=self.state_topic_retain)

    def on_command_message(self, client, userdata, msg):
        self.logger.debug("Command message {} recieved on {}".format(msg.payload, msg.topic))
        if msg.payload == self.payload_on \
                and not indigo.devices[self.parent_id].ledStates[self.button - 1]:
            if self.is_relay:
                indigo.relay.setLedState(self.parent_id,
                                         index=self.button - 1,
                                         value=True)
            else:
                indigo.dimmer.setLedState(self.parent_id,
                                          index=self.button - 1,
                                          value=True)
        elif msg.payload == self.payload_off \
                and indigo.devices[self.parent_id].ledStates[self.button - 1]:
            if self.is_relay:
                indigo.relay.setLedState(self.parent_id,
                                         index=self.button - 1,
                                         value=False)
            else:
                indigo.dimmer.setLedState(self.parent_id,
                                          index=self.button - 1,
                                          value=False)


class InsteonButtonActivityTracker(BaseHAEntity, InsteonCommandProcessor):
    TOPIC_KEY = "topic"
    DEFAULT_TOPIC = TOPIC_ROOT + "/trigger"
    PAYLOAD_KEY = "payload"
    DEFAULT_PAYLOAD = "triggered"
    TYPE_KEY = "type"
    SUBTYPE_KEY = "subtype"
    AUTOMATION_TYPE_KEY = "automation_type"
    DEFAULT_AUTOMATION_TYPE = "trigger"

    def __init__(self, indigo_entity, overrides, logger,
                 discovery_prefix, button, label, activity_type):
        self.button = button
        self.label = label
        self.activity_type = activity_type
        super(InsteonButtonActivityTracker, self).__init__(indigo_entity,
                                                           overrides,
                                                           logger,
                                                           discovery_prefix)
        self.id = "{}_{}_{}".format(indigo_entity.id, self.button, self.activity_type)
        self.config = {
            self.AUTOMATION_TYPE_KEY: self.DEFAULT_AUTOMATION_TYPE,
            self.TOPIC_KEY: self.topic,
            self.TYPE_KEY: self.activity_type,
            self.SUBTYPE_KEY: self.subtype,
            self.PAYLOAD_KEY: self.payload,
            self.CONFIG_QOS: self.qos,
            'device': {
                'identifiers': [indigo_entity.address, indigo_entity.id],
                'manufacturer': '{} via Indigo MQTT Bridge'.format(indigo_entity.protocol),
                'model': indigo_entity.model,
                'name': indigo_entity.name
            }}

    @property
    def hass_type(self):
        return "device_automation"

    @property
    def subtype(self):
        return self._overrideable_get(self.SUBTYPE_KEY, "Button {}".format(self.label)).format(d=self)

    @property
    def name(self):
        return self._overrideable_get(self.CONFIG_NAME, self.indigo_entity.name +
                                      " Button {} {}".format(self.label, self.activity_type)).format(d=self)

    @property
    def mqtt_name(self):
        name = self._overrideable_get(self.CONFIG_NAME, self.indigo_entity.name + " Button {} {}"
                                      .format(self.label, self.activity_type)).format(d=self).lower()
        name = re.sub(r"[^\w\s]", '', name)
        name = re.sub(r"\s+", '_', name)
        return name

    @property
    def payload(self):
        return self._overrideable_get(self.CONFIG_NAME, self.DEFAULT_PAYLOAD).format(d=self)

    @property
    def topic(self):
        return self._overrideable_get(self.TOPIC_KEY, self.DEFAULT_TOPIC).format(d=self)

    def process_command(self, cmd, config):
        if cmd.cmdScene == self.button and INSTEON_EVENTS[cmd.cmdFunc] == self.activity_type:
            __main__.get_mqtt_client().publish(topic=self.topic,
                                     payload=self.payload,
                                     qos=self.qos,
                                     retain=False)
        return None, None


class InsteonRemote(Base, InsteonRemoteCommandProcessor):

    def __init__(self, indigo_entity, overrides, logger, button, label):
        self.button = button
        self.label = label
        super(InsteonRemote, self).__init__(indigo_entity, overrides, logger)
        self.id = "{}_{}".format(indigo_entity.id, button) if self.label else indigo_entity.id

    @property
    def name(self):
        extention = " Button {}".format(self.label) if self.label else " Button"
        return self._overrideable_get(self.CONFIG_NAME, self.indigo_entity.name + extention).format(d=self)


class InsteonBatteryStateSensor(BinarySensor, TimedUpdateCheck):
    def __init__(self, indigo_entity, overrides, logger, discovery_prefix):
        super(InsteonBatteryStateSensor, self).__init__(indigo_entity, overrides, logger, discovery_prefix)
        self.id = "{}_battery".format(indigo_entity.id)

    DEFAULT_DEVICE_CLASS = "battery"

    @property
    def name(self):
        return self._overrideable_get(self.CONFIG_NAME, self.indigo_entity.name + " Battery").format(d=self)

    def update(self, orig_dev, new_dev):
        pass

    def check_for_update(self):
        state = False
        tz = tzlocal.get_localzone()  # local timezone
        then = tz.normalize(tz.localize(self.indigo_entity.lastSuccessfulComm))  # make it timezone-aware
        now = datetime.now(tz)  # timezone-aware current time in the local timezone
        if (now - then) > timedelta(1):
            state = True
        self._send_battery_state(state)
        self._send_attributes(self.indigo_entity)

    def _send_battery_state(self, battery_state):
        state = self.payload_on if battery_state else self.payload_off
        __main__.get_mqtt_client().publish(topic=self.state_topic,
                                 payload=state,
                                 qos=self.state_topic_qos,
                                 retain=self.state_topic_retain)
