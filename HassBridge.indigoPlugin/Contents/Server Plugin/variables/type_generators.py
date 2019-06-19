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

from .devices import VariableBinarySensor, VariableSensor


class VariableDefaultTypesGenerator(object):

    @staticmethod
    def generate(variable, config, logger):
        variables = {}
        overrides = {}

        if variable.value.lower() in ['true', 'false']:
            bridge_type = VariableBinarySensor.__name__
        else:
            bridge_type = VariableSensor.__name__

        if 'variables' in config.customizations and variable.name in config.customizations['variables']:
            overrides = config.customizations['variables'][variable.name]

        if 'bridge_type' in overrides:
            bridge_type = overrides['bridge_type']

        if bridge_type and bridge_type in globals():
            hass_dev = globals()[bridge_type](variable, overrides, logger, config.hass_discovery_prefix)
            variables[str(variable.id)] = hass_dev

        return variables

    @staticmethod
    def is_bridgeable(dev, logger):
        return True
