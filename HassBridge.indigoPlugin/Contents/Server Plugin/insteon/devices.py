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
from hass_devices import BinarySensor, Cover, Fan, Light, Lock, Sensor, Switch
from hass_devices.base import Base, BaseCommandableHADevice, BaseHAEntity
from hassbridge import TOPIC_ROOT, TimedUpdateCheck, get_mqtt_client

from .command_processors import (
    INSTEON_EVENTS, InsteonCommandProcessor,
    InsteonGeneralCommandProcessor, InsteonKeypadButtonCommandProcessor,
    InsteonRemoteCommandProcessor)


class InsteonBinarySensor(BinarySensor):
    pass


class InsteonSensor(Sensor):
    pass


class InsteonSwitch(Switch, InsteonGeneralCommandProcessor):
    pass


class InsteonLight(Light, InsteonGeneralCommandProcessor):
    pass


class InsteonLock(Lock, InsteonGeneralCommandProcessor):
    pass


class InsteonFan(Fan):
    pass


class InsteonCover(Cover):
    pass


class InsteonKeypadButtonLight(Switch, InsteonKeypadButtonCommandProcessor):
    # pylint: disable=too-many-arguments
    def __init__(self, indigo_entity, overrides, logger,
                 discovery_prefix, button, label):
        self.is_relay = False
        self.button = button
        self.label = label
        super(InsteonKeypadButtonLight, self).__init__(indigo_entity,
                                                       overrides,
                                                       logger,
                                                       discovery_prefix)
        self.id = "{}_{}".format(indigo_entity.id, button)
        self.parent_id = indigo_entity.id

    @property
    def hass_type(self):
        return "light"

    @property
    def name(self):
        return self._overrideable_get(
            self.CONFIG_NAME,
            self.indigo_entity.name + " Button {}".format(
                self.label)).format(d=self)

    @property
    def mqtt_name(self):
        name = self._overrideable_get(
            self.CONFIG_NAME,
            self.indigo_entity.name + " Button {}".format(
                self.label)).format(d=self).lower()
        name = re.sub(r"[^\w\s]", '', name)
        name = re.sub(r"\s+", '_', name)
        return name

    # pylint: disable=unused-argument
    def update(self, orig_dev, new_dev):
        self._send_state(new_dev)

    def _send_state(self, dev):
        state = self.payload_on if dev.ledStates[
            self.button - 1] else self.payload_off
        get_mqtt_client().publish(topic=self.state_topic,
                                  payload=state,
                                  qos=self.state_topic_qos,
                                  retain=self.state_topic_retain)

    # pylint: disable=unused-argument
    def on_command_message(self, client, userdata, msg):
        self.logger.debug(
            u'Command message {} recieved on {}'.format(msg.payload, msg.topic))
        if msg.payload == self.payload_on \
                and not \
                indigo.devices[self.parent_id].ledStates[self.button - 1]:
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

    # pylint: disable=too-many-arguments
    def __init__(self, indigo_entity, overrides, logger,
                 discovery_prefix, button, label, activity_type):
        self.button = button
        self.label = label
        self.activity_type = activity_type
        super(InsteonButtonActivityTracker, self).__init__(indigo_entity,
                                                           overrides,
                                                           logger,
                                                           discovery_prefix)
        self.id = "{}_{}_{}".format(indigo_entity.id, self.button,
                                    self.activity_type)
        self.config = {
            self.AUTOMATION_TYPE_KEY: self.DEFAULT_AUTOMATION_TYPE,
            self.TOPIC_KEY: self.topic,
            self.TYPE_KEY: self.activity_type,
            self.SUBTYPE_KEY: self.subtype,
            self.PAYLOAD_KEY: self.payload,
            self.CONFIG_QOS: self.qos,
            'device': {
                'identifiers': [indigo_entity.address, indigo_entity.id],
                'manufacturer': '{} via Indigo MQTT Bridge'.format(
                    indigo_entity.protocol),
                'model': indigo_entity.model,
                'name': indigo_entity.name
            }}

    @property
    def hass_type(self):
        return "device_automation"

    @property
    def subtype(self):
        return self._overrideable_get(
            self.SUBTYPE_KEY,
            "Button {}".format(self.label)).format(d=self)

    @property
    def name(self):
        return self._overrideable_get(
            self.CONFIG_NAME,
            self.indigo_entity.name + " Button {} {}".format(
                self.label, self.activity_type)).format(d=self)

    @property
    def mqtt_name(self):
        name = self._overrideable_get(self.CONFIG_NAME,
                                      self.indigo_entity.name + " Button {} {}"
                                      .format(self.label,
                                              self.activity_type)) \
            .format(d=self).lower()
        name = re.sub(r"[^\w\s]", '', name)
        name = re.sub(r"\s+", '_', name)
        return name

    @property
    def payload(self):
        return self._overrideable_get(self.CONFIG_NAME,
                                      self.DEFAULT_PAYLOAD).format(d=self)

    @property
    def topic(self):
        return self._overrideable_get(self.TOPIC_KEY,
                                      self.DEFAULT_TOPIC).format(d=self)

    def process_command(self, cmd, config):
        if cmd.cmdScene == self.button and \
                INSTEON_EVENTS[cmd.cmdFunc] == self.activity_type:
            get_mqtt_client().publish(topic=self.topic,
                                      payload=self.payload,
                                      qos=self.qos,
                                      retain=False)
        return None, None


class InsteonRemote(Base, InsteonRemoteCommandProcessor):
    # pylint: disable=too-many-arguments
    def __init__(self, indigo_entity, overrides, logger, button, label):
        self.button = button
        self.label = label
        super(InsteonRemote, self).__init__(indigo_entity, overrides, logger)
        self.id = "{}_{}".format(indigo_entity.id,
                                 button) if self.label else indigo_entity.id

    @property
    def name(self):
        extention = " Button {}".format(self.label) if self.label else " Button"
        return self._overrideable_get(
            self.CONFIG_NAME,
            self.indigo_entity.name + extention).format(d=self)


class InsteonBatteryStateSensor(BinarySensor, TimedUpdateCheck):
    # pylint: disable=too-many-arguments
    def __init__(self, indigo_entity, overrides, logger, discovery_prefix,
                 no_comm_minutes):
        super(InsteonBatteryStateSensor, self).__init__(indigo_entity,
                                                        overrides, logger,
                                                        discovery_prefix)
        self.id = "{}_battery".format(indigo_entity.id)
        self.no_comm_minutes = no_comm_minutes

    DEFAULT_DEVICE_CLASS = "battery"

    @property
    def name(self):
        return self._overrideable_get(
            self.CONFIG_NAME,
            self.indigo_entity.name + " Battery").format(d=self)

    def update(self, orig_dev, new_dev):
        pass

    def check_for_update(self):
        state = False
        tz = tzlocal.get_localzone()  # local timezone
        then = tz.normalize(tz.localize(
            self.indigo_entity.lastSuccessfulComm))  # make it timezone-aware
        now = datetime.now(
            tz)  # timezone-aware current time in the local timezone
        if (now - then) > timedelta(minutes=self.no_comm_minutes):
            state = True
        self._send_battery_state(state)
        self._send_attributes(self.indigo_entity)

    def _send_battery_state(self, battery_state):
        state = self.payload_on if battery_state else self.payload_off
        get_mqtt_client().publish(topic=self.state_topic,
                                  payload=state,
                                  qos=self.state_topic_qos,
                                  retain=self.state_topic_retain)


class InsteonLedBacklight(Light, InsteonGeneralCommandProcessor):
    BACKLIGHT_SET_MECHANISM_KEY = "backlight_set_mechansim"
    DEFAULT_BACKLIGHT_SET_MECHANISM = "kpl"

    def __init__(self, indigo_entity, overrides, logger, discovery_prefix):
        super(InsteonLedBacklight, self).__init__(indigo_entity,
                                                  overrides,
                                                  logger,
                                                  discovery_prefix)
        self.id = "{}_backlight".format(indigo_entity.id)
        self.parent_id = indigo_entity.id
        self.switch_state = self.payload_on
        self.brightness_level = 100

    @property
    def name(self):
        return self._overrideable_get(
            self.CONFIG_NAME,
            self.indigo_entity.name + " Backlight").format(d=self)

    @property
    def backlight_set_mechansim(self):
        return self._overrideable_get(
            self.BACKLIGHT_SET_MECHANISM_KEY,
            self.DEFAULT_BACKLIGHT_SET_MECHANISM,
            self.MAIN_CONFIG_SECTION).format(d=self)

    def update(self, orig_dev, new_dev):
        pass

    def register(self):
        BaseCommandableHADevice.register(self)
        # register brightness command topic
        self.logger.debug(
            u'Subscribing {} with id {}:{} to brightness command topic {}'
                .format(
                self.hass_type,
                self.name,
                self.id,
                self.brightness_command_topic))
        get_mqtt_client().message_callback_add(
            self.brightness_command_topic,
            self.on_brightness_command_message)
        get_mqtt_client().subscribe(self.brightness_command_topic)
        self._send_brightness_state(self.indigo_entity)

    # pylint: disable=unused-argument
    def _send_state(self, dev):
        get_mqtt_client().publish(
            topic=self.state_topic,
            payload=self.switch_state,
            qos=self.state_topic_qos,
            retain=self.state_topic_retain)

    # pylint: disable=unused-argument
    def _send_brightness_state(self, dev):
        self.logger.debug(u'Sending brightness state of {} to {}'
                          .format(self.brightness_level,
                                  self.brightness_state_topic))
        get_mqtt_client().publish(
            topic=self.brightness_state_topic,
            payload=unicode(self.brightness_level),
            retain=self.brightness_command_topic_retain)

    # pylint: disable=unused-argument
    def on_brightness_command_message(self, client, userdata, msg):
        self.logger.debug(u'Brightness Command message {} recieved on {}'
                          .format(msg.payload, msg.topic))

        if int(msg.payload) > 0:
            self._turn_on_backlight()
            self._set_backlight_brightness(int(msg.payload))
            self.brightness_level = int(msg.payload)
        else:
            self._turn_off_backlight()
            self.brightness_level = 0
        self._send_brightness_state(self.indigo_entity)

    def on_command_message(self, client, userdata, msg):
        self.logger.debug(
            u"Command message {} recieved on {}".format(msg.payload,
                                                        msg.topic))
        if msg.payload == self.payload_on:
            self._turn_on_backlight()
            self.switch_state = self.payload_on
        elif msg.payload == self.payload_off:
            self._turn_off_backlight()
            self.switch_state = self.payload_off

        self._send_state(self.indigo_entity)

    def _turn_off_backlight(self):
        led_off_command = [0x20, 0x08, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
                           0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
        try:
            indigo.insteon.sendRawExtended(self.indigo_entity.address,
                                           led_off_command)
        except Exception:  # pylint: disable=broad-except
            self.logger.error(
                u'Unable to turn off backlight for ' % self.name)

    def _turn_on_backlight(self):
        led_on_command = [0x20, 0x09, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
                          0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
        try:
            indigo.insteon.sendRawExtended(self.indigo_entity.address,
                                           led_on_command)
        except Exception:  # pylint: disable=broad-except
            self.logger.error(
                u'Unable to turn on backlight for ' % self.name)

    def _set_backlight_brightness(self, level):
        if self.backlight_set_mechansim == 'kpl':
            level = (((level - 0) * (127 - 5)) / (100 - 0)) + 5
            d1 = 0x00
            d2 = 0x07
        elif self.backlight_set_mechansim == 'swl':
            level = (((level - 0) * (255 - 1)) / (100 - 0)) + 1
            d1 = 0x01
            d2 = 0x03
        else:
            self.logger.error(
                u'Unknown led backlight set mechanism "{}" for {}'.format(
                    self.backlight_set_mechansim, self.indigo_entity.name))
            return

        try:

            led_brightness_command = [0x2E, 0x00, d1, d2, level, 0x00, 0x00,
                                      0x00, 0x00, 0x00, 0x00,
                                      0x00, 0x00, 0x00, 0x00, 0x00]
            indigo.insteon.sendRawExtended(self.indigo_entity.address,
                                           led_brightness_command)
        except Exception:  # pylint: disable=broad-except
            self.logger.error(
                u'Unable to set backlight brightness for {}' % self.name)
