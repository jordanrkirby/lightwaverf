from homeassistant.const import TEMP_CELSIUS
from homeassistant.components.scene import Scene
from homeassistant.helpers.entity import generate_entity_id
#import homeassistant.loader as loader
import custom_components.lwrf as lwrf

import logging
import lightwaverf
import calendar
import time

DEPENDENCIES = ['lwrf','group']

def setup_platform(hass, config, add_devices, discovery_info=None):
    l = lwrf.LWHUB

    if len(l.events) == 0:
        return

    event_items = [LWRFEvent(e) for e in l.events]

    new_event_items = []
    for e in event_items:
        if e.name not in lwrf.LW_KNOWN_EVENTS:
            lwrf.LW_KNOWN_EVENTS.append(e.name)
            new_event_items.append(e)
            add_devices([e])

    #group = loader.get_component('group')

    #group_name = "Events"
    #if group_name not in lwrf.LW_KNOWN_GROUPS:
    #    group.Group(hass, group_name, [d.entity_id for d in new_event_items], view=True)
    #    lwrf.LW_KNOWN_GROUPS.append(group_name)

class LWRFEvent(Scene):

    def __init__(self, event):
        self.__event = event

    @property
    def entity_id(self):
        return "scene.lwrf_{}".format(self.name.lower().replace(' ','_'))

    @property
    def name(self):
        return self.__event.name.title() + " Scene"

    @property
    def icon(self):
        return "mdi:google-circles-extended"
    @property
    def state(self):
        """Return the state of the scene."""
        return True

    def activate(self):
        """Activate scene. Try to get entities into requested state."""
        self.__event.start()
        return True
