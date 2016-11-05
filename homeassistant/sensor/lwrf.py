from homeassistant.const import TEMP_CELSIUS
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity import generate_entity_id
#import homeassistant.loader as loader
import custom_components.lwrf as lwrf

import logging
import lightwaverf
import calendar
import time

DEPENDENCIES = ['lwrf','group']

def setup_platform(hass, config, add_devices, discovery_info=None):
    #group = loader.get_component('group')
    l = lwrf.LWHUB

    if l.energy is None:
        return

    if len(lwrf.LW_KNOWN_ENERGY) < 2:
        energy_devices = [LWRFEnergy(l.energy, "current"), LWRFEnergy(l.energy, "today")]
        add_devices(energy_devices)
        lwrf.LW_KNOWN_ENERGY = energy_devices

    hub_device = [LWRFHubVersion(l)]
    add_devices(hub_device)
    lwrf.LW_HUB_VERISON = hub_device

class LWRFHubVersion(Entity):
    _hub = None

    def __init__(self, hub):
        self._hub = hub

    @property
    def entity_id(self):
        return "sensor.lwrf_{}".format(self.name.lower().replace(' ','_'))

    @property
    def name(self):
        return "Hub Version"

    @property
    def state(self):
        try:
            return getattr(self.version)
        except AttributeError:
            return None

    @property
    def unit_of_measurement(self):
        return None

class LWRFEnergy(Entity):
    energy = None

    def __init__(self, energy_meter, meter):
        self.energy = energy_meter
        self.meter = meter

    @property
    def entity_id(self):
        return "sensor.lwrf_{}".format(self.name.lower().replace(' ','_'))

    @property
    def name(self):
        return (self.energy.name + ' Energy ' + self.meter).title()

    @property
    def icon(self):
        return "mdi:speedometer"

    @property
    def state(self):
        try:
            return getattr(self.energy, self.meter)
        except AttributeError:
            return None

    @property
    def unit_of_measurement(self):
        return "KWh"
