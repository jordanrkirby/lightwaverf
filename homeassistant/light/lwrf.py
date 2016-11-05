import logging
import lightwaverf
import calendar
import time
from homeassistant.components.light import (Light, ATTR_BRIGHTNESS)
from homeassistant.helpers.entity import generate_entity_id
import custom_components.lwrf as lwrf
#import homeassistant.loader as loader

DEPENDENCIES = ['lwrf','group']

def setup_platform(hass, config, add_devices, discovery_info=None):
    #group = loader.get_component('group')
    l = lwrf.LWHUB

    if len(l.lights) == 0:
        return

    lighting_devices = [LWRFLight(light) for light in l.lights]

    for light in lighting_devices:
        if light.name not in lwrf.LW_KNOWN_LIGHTS:
            lwrf.LW_KNOWN_LIGHTS.append(light.name)
            add_devices([light])

    #rooms = {}

    # for d in lighting_devices:
        #rooms.setdefault(d._light.room_name, []).append(d.entity_id)

    #for r, d in rooms.items():
    #    if r + " Lights" not in lwrf.LW_KNOWN_GROUPS and r is not None:
    #        lwrf.LW_KNOWN_GROUPS.append(r + " Lights")
    #        group.Group(hass, r + " Lights", d)

    # now do the timers!
    timers = [LWRFTimer(t) for t in l.timers]

    for timer in timers:
        if timer.name not in lwrf.LW_KNOWN_TIMERS:
            lwrf.LW_KNOWN_TIMERS.append(timer.name)
            add_devices([timer])

    #if "Timers" not in lwrf.LW_KNOWN_GROUPS:
    #    group.Group(hass, "Timers", [t.entity_id for t in timers])
        #group.Group(hass, "Timers", ["group.timers"], view=True, icon="mdi:av-timer")
    #    lwrf.LW_KNOWN_GROUPS.append("Timers")

class LWRFLight(Light):
    _light = None
    def __init__(self, light, brightness=None):
        self._light = light
        self.brightness = brightness

    @property
    def entity_id(self):
        return "light.lwrf_{}".format(self.name.lower().replace(' ','_'))

    @property
    def name(self):
        """Return the display name of this light"""
        return (self._light.room_name + ' ' + self._light.name).title()

    @property
    def icon(self):
        return "mdi:lightbulb-outline"

    @property
    def brightness(self):
        """Brightness of the light (an integer in the range 1-255).

        This method is optional. Removing it indicates to Home Assistant
        that brightness is not supported for this light.
        """
        return self._light.brightness

    @brightness.setter
    def brightness (self, value):
        if value is not None:
            self._light.brightness = value

    @property
    def is_on(self):
        """If light is on."""
        return self._light.state

    def turn_on(self, **kwargs):
        """Instruct the light to turn on.

        You can skip the brightness part if your light does not support
        brightness control.
        """
        self._light.brightness = kwargs.get(ATTR_BRIGHTNESS, 255)
        self._light.turn_on()

    def turn_off(self, **kwargs):
        """Instruct the light to turn off."""
        self._light.turn_off()

    def update(self):
        """Fetch new state data for this light.

        This is the only method that should fetch new data for Home Assitant.
        """
        self._light.state

#    @property
#    def assumed_state(self):
#        return True

class LWRFTimer(Light):
    _timer = None

    def __init__(self, timer):
        self._timer = timer
        logging.info("Timer: " + self._timer.name)
        logging.info("Active: " + str(self._timer.active))
        logging.info("Bool Active: " + str(bool(self._timer.active)))

    @property
    def entity_id(self):
        return "light.lwrf_timer_{}".format(self.name.lower().replace(' ','_'))

    @property
    def name(self):
        """Return the display name of this light"""
        return self._timer.name.title() + " Timer"

    @property
    def assumed_state(self):
        return True

    @property
    def icon(self):
        return "mdi:av-timer"

    @property
    def is_on(self):
        """If light is on."""
        return bool(self._timer.active)

    def turn_on(self, **kwargs):
        """Instruct the light to turn on.
        You can skip the brightness part if your light does not support
        brightness control.
        """
        self._timer.start()

    def turn_off(self, **kwargs):
        """Instruct the light to turn off."""
        self._timer.pause()

    def should_poll(self):
        return False

    def update(self):
        """Fetch new state data for this light.

        This is the only method that should fetch new data for Home Assitant.
        """
        return bool(self._timer.active)
