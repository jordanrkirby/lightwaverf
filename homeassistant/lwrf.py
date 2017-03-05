#from homeassistant.components.discovery import load_platform
from homeassistant.helpers.discovery import load_platform
import lightwaverf
#import homeassistant.loader as loader
import logging
import time

DEPENDENCIES = ['group']

DOMAIN = 'lwrf'
LWHUB = None
G_HASS = None
LWCONFIG = None

LW_KNOWN_GROUPS = []
LW_KNOWN_ROOMS = []
LW_KNOWN_LIGHTS = []
LW_KNOWN_SOCKETS = []
LW_KNOWN_HEATING = []
LW_KNOWN_EVENTS = []
LW_KNOWN_TIMERS = []
LW_KNOWN_ENERGY = []
LW_HUB_VERISON = None
def load_subcomponents():
    global DOMAIN
    global G_HASS
    global LWHUB
    global LWCONFIG
    global LW_KNOWN_ROOMS
    global LW_KNOWN_GROUPS

    load_platform(G_HASS, 'sensor', DOMAIN)
    load_platform(G_HASS, 'climate', DOMAIN)
    load_platform(G_HASS, 'light', DOMAIN)
    load_platform(G_HASS, 'switch', DOMAIN)
    load_platform(G_HASS, 'scene', DOMAIN)

    #group = loader.get_component('group')

    #if 'rooms' in LWCONFIG['lwrf'] and len(LWHUB.rooms) > 0:
    #    if LWCONFIG['lwrf']['rooms'] == "yes" or LWCONFIG['lwrf']['rooms'] == True:
    #        logging.info("Display LightwaveRF Rooms")
    #        for r in LWHUB.rooms:
    #            if len(r.devices) > 0 and r.name not in LW_KNOWN_GROUPS:
    #                LW_KNOWN_GROUPS.append(r.name)
    #                group.Group(G_HASS, r.name, ["group." + r.name.replace(" ","_").lower() + "_lights","group." + r.name.replace(" ","_").lower() + "_switches","group." + r.name.replace(" ","_").lower() + "_heating"], view=True)
    #    elif LWCONFIG['lwrf']['rooms'] == "broad":
    #        logging.info("Display LightwaveRF Rooms and Media Players")
    #        for r in LWHUB.rooms:
    #            if len(r.devices) > 0 and r.name not in LW_KNOWN_GROUPS:
    #                LW_KNOWN_GROUPS.append(r.name)
    #                group.Group(G_HASS, r.name, ["group." + r.name.replace(" ","_").lower() + "_lights","group." + r.name.replace(" ","_").lower() + "_switches","group." + r.name.replace(" ","_").lower() + "_heating","media_player."+ r.name.replace(" ","_").lower()],view=True)

def setup(hass, config):
    """Your controller/hub specific code."""
    global LWHUB
    global G_HASS
    global LWCONFIG

    LWCONFIG = config
    G_HASS = hass

    if LWHUB is None:
        l = lightwaverf.LWRFServer(username=config['lwrf']['username'],pin=config['lwrf']['pin'],log="warning")
        l._discovery_obeservers.append(load_subcomponents)
        l.start_server(True)
        LWHUB = l

    load_subcomponents()

    return True
