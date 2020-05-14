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

import __main__
from hassbridge import str2bool

from .base import BaseStatefulHADevice


class Sensor(BaseStatefulHADevice):

    def __init__(self, indigo_entity, overrides, logger, discovery_prefix):
        super(Sensor, self).__init__(indigo_entity,
                                     overrides,
                                     logger,
                                     discovery_prefix)
        self.config.update({
            self.EXPIRE_AFTER_KEY: self.expire_after,
            self.FORCE_UPDATE_KEY: self.force_update
        })
        self.config.update({
            self.UNIT_OF_MEASUREMENT_KEY: self.unit_of_measurement})
        self.config.update({self.DEVICE_CLASS_KEY: self.device_class})
        del self.config[self.PAYLOAD_ON_KEY]
        del self.config[self.PAYLOAD_OFF_KEY]

    @property
    def hass_type(self):
        return "sensor"

    DEVICE_CLASS_KEY = "device_class"
    DEFAULT_DEVICE_CLASS = "None"

    @property
    def device_class(self):
        ret = self.DEFAULT_DEVICE_CLASS
        if self.indigo_entity.subModel == u'Humidity':
            ret = u'humidity'
        elif self.indigo_entity.subModel == u'Luminance':
            ret = u'illuminance'
        elif self.indigo_entity.subModel == u'Temperature':
            ret = u'temperature'
        ret = self._overrideable_get(self.DEVICE_CLASS_KEY,
                                     ret)
        return ret.format(d=self) if ret is not None else ret

    def _send_state(self, dev):
        __main__.get_mqtt_client().publish(topic=self.state_topic,
                                           payload=dev.sensorValue,
                                           retain=self.state_topic_retain)

    EXPIRE_AFTER_KEY = "expire_after"
    DEFAULT_EXPIRE_AFTER = 0

    @property
    def expire_after(self):
        return int(self._overrideable_get(
            self.EXPIRE_AFTER_KEY,
            self.DEFAULT_EXPIRE_AFTER).format(d=self))

    FORCE_UPDATE_KEY = "force_update"
    DEFAULT_FORCE_UPDATE = False

    @property
    def force_update(self):
        retval = self._overrideable_get(self.FORCE_UPDATE_KEY,
                                        self.DEFAULT_FORCE_UPDATE)
        return str2bool(retval.format(d=self))

    UNIT_OF_MEASUREMENT_KEY = "unit_of_measurement"
    DEFAULT_UNIT_OF_MEASUREMENT = ""

    @property
    def unit_of_measurement(self):
        ret = self.DEFAULT_UNIT_OF_MEASUREMENT
        if self.indigo_entity.subModel == u'Humidity':
            ret = u'%'
        elif self.indigo_entity.subModel == u'Luminance':
            ret = u'lx'
        elif self.indigo_entity.subModel == u'Temperature':
            ret = self.indigo_entity.states[u'sensorValue.ui'].split(' ')[-1]
        ret = self._overrideable_get(self.UNIT_OF_MEASUREMENT_KEY,
                                     ret)
        return ret.format(d=self) if ret is not None else ret
