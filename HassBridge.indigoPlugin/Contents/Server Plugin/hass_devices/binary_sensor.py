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

from hassbridge import str2bool
from .base import BaseStatefulHADevice



class BinarySensor(BaseStatefulHADevice):
    def __init__(self, indigo_entity, overrides, logger, discovery_prefix):
        super(BinarySensor, self).__init__(indigo_entity, overrides, logger, discovery_prefix)
        if self.device_class is not None:
            self.config.update({self.DEVICE_CLASS_KEY: self.device_class})
        if self.off_dely is not None:
            self.config.update({self.OFF_DELAY_KEY: self.off_dely})
        if self.value_template is not None:
            self.config.update({self.VALUE_TEMPLATE_KEY: self.value_template})
        self.config.update({self.FORCE_UPDATE_KEY: self.force_update})

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
