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

from hassbridge import CommandProcessor

INSTEON_EVENTS = {
    "on": "on",
    "on to 100% (instant)": "instant_on",
    "off": "off",
    "off (instant)": "instant_off",
    "start brighten": "start_brighten",
    "stop brighten": "stop_brighten",
    "start dim": "start_dim",
    "stop dim": "stop_dim"
}

INSTEON_LOW_BATTERY_EVENT = "low_battery"
INSTEON_REMOTE_LOW_BATTERY_SCENE = 9


class InsteonCommandProcessor(CommandProcessor):
    def process_command(self, cmd, config):
        self.logger.debug(
            u'HA Device {} processing Insteon Keypad Button command {} from {}'
                .format(self.ha_friendly_name, cmd.cmdFunc, self.indigo_entity.name))
        event = payload = None
        if cmd.cmdFunc is not None and cmd.cmdFunc in INSTEON_EVENTS:
            event = "{}_{}".format(config.hass_event_prefix, INSTEON_EVENTS[cmd.cmdFunc])
            payload = {
                "sender_id": self.ha_friendly_name.lower().replace(" ", "_"),
                "name": self.ha_friendly_name,
                "id": self.id,
                "address": cmd.address,
                "group": cmd.cmdScene
            }
        else:
            self.logger.warn(u'Untracked Insteon Keypad Button command {}'
                             .format(cmd.cmdFunc))
        return event, payload


class InsteonGeneralCommandProcessor(InsteonCommandProcessor):
    def process_command(self, cmd, config):
        if cmd.cmdScene == 1:
            return super(InsteonGeneralCommandProcessor, self)\
                .process_command(cmd, config)
        else:
            return None, None


class InsteonKeypadButtonCommandProcessor(InsteonCommandProcessor):
    def process_command(self, cmd, config):
        if cmd.cmdScene == self.button:
            return super(InsteonKeypadButtonCommandProcessor, self)\
                .process_command(cmd, config)
        else:
            return None, None


class InsteonRemoteCommandProcessor(InsteonKeypadButtonCommandProcessor):
    def process_command(self, cmd, config):
        if cmd.cmdScene == INSTEON_REMOTE_LOW_BATTERY_SCENE:
            return INSTEON_LOW_BATTERY_EVENT, {
                "sender_id": self.ha_friendly_name.lower().replace(" ", "_"),
                "name": self.ha_friendly_name,
                "id": self.id,
                "address": cmd.address,
                "group": cmd.cmdScene
            }
        return super(InsteonRemoteCommandProcessor, self)\
            .process_command(cmd, config)
