import logging
import lightwaverf
import calendar
import time
from homeassistant.components.switch import SwitchDevice
from homeassistant.helpers.entity import generate_entity_id

import custom_components.lwrf as lwrf
#import homeassistant.loader as loader

DEPENDENCIES = ['lwrf','group']

def setup_platform(hass, config, add_devices, discovery_info=None):
    #group = loader.get_component('group')
    l = lwrf.LWHUB

    if len(l.sockets) == 0:
        return
    socket_devices = [LWRFSwitch(socket) for socket in l.sockets]
    new_socket_devices = []

    for socket in socket_devices:
        if socket.name not in lwrf.LW_KNOWN_SOCKETS:
            lwrf.LW_KNOWN_SOCKETS.append(socket.name)
            new_socket_devices.append(socket)
            add_devices([socket])

    #rooms = {}

    #for d in socket_devices:
        #rooms.setdefault(d._socket.room_name, []).append(d.entity_id)

    #for r, d in rooms.items():
    #    if r + " Switches" not in lwrf.LW_KNOWN_GROUPS:
    #        lwrf.LW_KNOWN_GROUPS.append(r + " Switches")
    #        group.Group(hass, r + " Switches", d)

class LWRFSwitch(SwitchDevice):
    _socket = None
    def __init__(self, socket):
        self._socket = socket

    @property
    def entity_id(self):
        return "switch.lwrf_{}".format(self.name.lower().replace(' ','_').replace("'",""))

    @property
    def icon(self):
        return "mdi:power-socket"

    @property
    def name(self):
        """Return the display name of this light"""
        return (self._socket.room_name + ' ' + self._socket.name).title()

    @property
    def is_on(self):
        """If light is on."""
        return self._socket.state

    def turn_on(self, **kwargs):
        """Instruct the light to turn on.

        You can skip the brightness part if your light does not support
        brightness control.
        """
        self._socket.turn_on()

    def turn_off(self, **kwargs):
        """Instruct the light to turn off."""
        self._socket.turn_off()

    def update(self):
        """Fetch new state data for this light.

        This is the only method that should fetch new data for Home Assitant.
        """
        self._socket.state

    @property
    def assumed_state(self):
        return True
