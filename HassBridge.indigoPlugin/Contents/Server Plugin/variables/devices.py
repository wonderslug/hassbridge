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

from hassbridge import str2bool, TOPIC_ROOT, UpdatableDevice
import __main__

from hass_devices.base import BaseStatefulHAEntity


class BaseStatefulHAVariable(BaseStatefulHAEntity, UpdatableDevice):
    """ Provides the basics for a Stateful Entry such as a Variable """

    def __init__(self, indigo_variable, overrides, logger, discovery_prefix):
        super(BaseStatefulHAVariable, self).__init__(indigo_variable, overrides, logger, discovery_prefix)
        self.config['device'] = {
            "identifiers": [indigo_variable.name],
            "manufacturer": "Indigo variable {} via Indigo MQTT Bridge".format(indigo_variable.name),
            "model": "variable",
            "name": indigo_variable.name
        }

    STATE_TOPIC_KEY = "state_topic"
    DEFAULT_STATE_TOPIC = TOPIC_ROOT + "/state"

    def register(self):
        super(BaseStatefulHAVariable, self).register()
        self._send_state(self.indigo_entity)

    def update(self, old_var, new_var):
        self._send_state(new_var)

    def _send_state(self, var):
        __main__.get_mqtt_client().publish(topic=self.state_topic,
                                 payload=var.value,
                                 qos=self.state_topic_qos,
                                 retain=self.state_topic_retain)


class VariableBinarySensor(BaseStatefulHAVariable):

    def __init__(self, indigo_variable, overrides, logger, discovery_prefix):
        super(VariableBinarySensor, self).__init__(indigo_variable, overrides, logger, discovery_prefix)
        if self.device_class is not None:
            self.config.update({self.DEVICE_CLASS_KEY: self.device_class})
        if self.off_dely is not None:
            self.config.update({self.OFF_DELAY_KEY: self.off_dely})
        if self.value_template is not None:
            self.config.update({self.VALUE_TEMPLATE_KEY: self.value_template})
        self.config.update({self.FORCE_UPDATE_KEY: self.force_update})

    ON_VALUE = 'on_value'
    DEFAULT_ON_VALUE = 'true'

    @property
    def on_value(self):
        ret = self._overrideable_get(self.ON_VALUE, self.DEFAULT_ON_VALUE, self.MAIN_CONFIG_SECTION)
        return ret.format(d=self) if ret is not None else ret

    @property
    def hass_type(self):
        return "binary_sensor"

    DEVICE_CLASS_KEY = "device_class"
    DEFAULT_DEVICE_CLASS = None

    @property
    def device_class(self):
        ret = self._overrideable_get(self.DEVICE_CLASS_KEY, self.DEFAULT_DEVICE_CLASS)
        return ret.format(d=self) if ret is not None else ret

    OFF_DELAY_KEY = "off_delay"
    DEFAULT_OFF_DELAY = None

    @property
    def off_dely(self):
        ret = self._overrideable_get(self.OFF_DELAY_KEY, self.DEFAULT_OFF_DELAY)
        return int(ret.format(d=self)) if ret is not None else ret

    VALUE_TEMPLATE_KEY = "value_template"
    DEFAULT_VALUE_TEMPLATE = None

    @property
    def value_template(self):
        ret = self._overrideable_get(self.VALUE_TEMPLATE_KEY, self.DEFAULT_VALUE_TEMPLATE)
        return ret.format(d=self) if ret is not None else ret

    FORCE_UPDATE_KEY = "force_update"
    DEFAULT_FORCE_UPDATE = False

    @property
    def force_update(self):
        retval = self._overrideable_get(self.FORCE_UPDATE_KEY, self.DEFAULT_FORCE_UPDATE)
        return str2bool(retval.format(d=self))

    PAYLOAD_ON_KEY = "payload_on"
    DEFAULT_PAYLOAD_ON = "ON"

    @property
    def payload_on(self):
        return self._overrideable_get(self.PAYLOAD_ON_KEY, self.DEFAULT_PAYLOAD_ON).format(d=self)

    PAYLOAD_OFF_KEY = "payload_off"
    DEFAULT_PAYLOAD_OFF = "OFF"

    @property
    def payload_off(self):
        return self._overrideable_get(self.PAYLOAD_OFF_KEY, self.DEFAULT_PAYLOAD_OFF).format(d=self)

    def _send_state(self, var):
        state = self.payload_on if var.value == self.on_value else self.payload_off
        __main__.get_mqtt_client().publish(topic=self.state_topic,
                                 payload=state,
                                 qos=self.state_topic_qos,
                                 retain=self.state_topic_retain)


class VariableSensor(BaseStatefulHAVariable):

    def __init__(self, indigo_variable, overrides, logger, discovery_prefix):
        super(VariableSensor, self).__init__(indigo_variable, overrides, logger, discovery_prefix)
        self.config.update({
            self.EXPIRE_AFTER_KEY: self.expire_after,
            self.FORCE_UPDATE_KEY: self.force_update
        })
        if self.unit_of_measurement is not None:
            self.config.update({self.UNIT_OF_MEASUREMENT_KEY: self.unit_of_measurement})

    EXPIRE_AFTER_KEY = "expire_after"
    DEFAULT_EXPIRE_AFTER = 0

    @property
    def hass_type(self):
        return "sensor"

    @property
    def expire_after(self):
        return int(self._overrideable_get(self.EXPIRE_AFTER_KEY, self.DEFAULT_EXPIRE_AFTER).format(d=self))

    FORCE_UPDATE_KEY = "force_update"
    DEFAULT_FORCE_UPDATE = False

    @property
    def force_update(self):
        retval = self._overrideable_get(self.FORCE_UPDATE_KEY, self.DEFAULT_FORCE_UPDATE)
        return str2bool(retval.format(d=self))

    UNIT_OF_MEASUREMENT_KEY = "unit_of_measurement"
    DEFAULT_UNIT_OF_MEASUREMENT = None

    @property
    def unit_of_measurement(self):
        ret = self._overrideable_get(self.UNIT_OF_MEASUREMENT_KEY, self.DEFAULT_UNIT_OF_MEASUREMENT)
        return ret.format(d=self) if ret is not None else ret
