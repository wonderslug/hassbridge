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

from hass_devices import BinarySensor, Fan, Light, Sensor, Switch
from hassbridge import TimedUpdateCheck, TOPIC_ROOT
import __main__


class ZWaveSwitch(Switch):
    def __init__(self, indigo_entity, overrides, logger, discovery_prefix):
        super(ZWaveSwitch, self).__init__(indigo_entity,
                                          overrides, logger, discovery_prefix)


class ZWaveLight(Light):
    def __init__(self, indigo_entity, overrides, logger, discovery_prefix):
        super(ZWaveLight, self).__init__(indigo_entity, overrides, logger,
                                         discovery_prefix)


class ZWaveFan(Fan):
    def __init__(self, indigo_entity, overrides, logger, discovery_prefix):
        super(ZWaveFan, self).__init__(indigo_entity, overrides, logger,
                                       discovery_prefix)


class ZWaveBinarySensor(BinarySensor):
    def __init__(self, indigo_entity, overrides, logger, discovery_prefix):
        super(ZWaveBinarySensor, self).__init__(indigo_entity, overrides,
                                                logger, discovery_prefix)


class ZWaveSensor(Sensor):
    def __init__(self, indigo_entity, overrides, logger, discovery_prefix):
        super(ZWaveSensor, self).__init__(indigo_entity, overrides, logger,
                                          discovery_prefix)


class ZWaveBatteryStateSensor(Sensor, TimedUpdateCheck):
    def __init__(self, indigo_entity, overrides, logger, discovery_prefix):
        super(ZWaveBatteryStateSensor, self).__init__(indigo_entity, overrides,
                                                      logger, discovery_prefix)
        self.id = "{}_battery".format(indigo_entity.id)
        self.config.update({self.DEVICE_CLASS_KEY: self.device_class})

    DEFAULT_DEVICE_CLASS = "battery"
    DEFAULT_UNIT_OF_MEASURE = '%'

    @property
    def name(self):
        return self._overrideable_get(self.CONFIG_NAME, self.indigo_entity.name
                                      + " Battery").format(d=self)
    @property
    def unit_of_measurement(self):
        return self._overrideable_get(self.UNIT_OF_MEASUREMENT_KEY,
                                      self.DEFAULT_UNIT_OF_MEASURE
                                      ).format(d=self)

    def update(self, orig_dev, new_dev):
        pass

    def check_for_update(self):
        state = 0
        if self.indigo_entity.batteryLevel is not None:
            state = self.indigo_entity.batteryLevel
        self._send_battery_state(state)
        self._send_attributes(self.indigo_entity)

    def _send_battery_state(self, battery_state):
        __main__.get_mqtt_client().publish(topic=self.state_topic,
                                           payload=battery_state,
                                           qos=self.state_topic_qos,
                                           retain=self.state_topic_retain)
