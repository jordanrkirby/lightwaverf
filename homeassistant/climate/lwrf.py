from homeassistant.const import TEMP_CELSIUS
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity import generate_entity_id
# import homeassistant.loader as loader
import custom_components.lwrf as lwrf
from homeassistant.components.climate import ClimateDevice

import logging
import lightwaverf
import calendar
import time

DEPENDENCIES = ['lwrf','group']

def setup_platform(hass, config, add_devices, discovery_info=None):
	#group = loader.get_component('group')
	l = lwrf.LWHUB

	if len(l.heating) == 0:
		return

	heating_devices = []
	rooms = {}

	for h in l.heating:
		if type(h) is lightwaverf.LightwaveRFThermostat:
			heating_devices.append(LWRFThermostat(h))
		else:
			heating_devices.append(LWRFHeating(h))

	for h in heating_devices:
		if h.name not in lwrf.LW_KNOWN_HEATING:
			add_devices(heating_devices)
			lwrf.LW_KNOWN_HEATING.append(h.name)

	for d in heating_devices:
		rooms.setdefault(d._heating.room_name, []).append(d.entity_id)

	#for r, d in rooms.items():
	#    group.Group(hass, r + " heating", d)

	#group.Group(hass, 'heating', [h.entity_id for h in heating_devices])

class LWRFHeating(ClimateDevice):
	_heating = None

	last_update = calendar.timegm(time.gmtime())

	def __init__(self, heating):
		self._heating = heating

	@property
	def entity_id(self):
		return "climate.lwrf_{}".format(self.name.lower().replace(' ','_'))

	def _check_update(self):
		if calendar.timegm(time.gmtime()) > self.last_update + 1800:
			logging.info("Updating " + self._heating.name + " Temperature now...")
			self._heating.refresh()
			self.last_update = calendar.timegm(time.gmtime())

	@property
	def icon(self):
		return "mdi:radiator"

	@property
	def state(self):
		try:
			return self._heating.current
		except AttributeError:
			return None

	@property
	def name(self):
		"""Return the name of the climate device."""
		return (self._heating.name).title()

	@property
	def unit_of_measurement(self):
		"""Return the unit of measurement."""
		return TEMP_CELSIUS

	@property
	def current_temperature(self):
		"""Return the current temperature."""
		try:
			return self._heating.current
		except AttributeError:
			return None

	@property
	def target_temperature(self):
		"""Return the temperature we try to reach."""
		try:
			return self._heating.target
		except AttributeError:
			return None

	def set_temperature(self, temperature):
		"""Set new target temperature."""
		self._heating.set_target_temperature(temperature)
		self.update_ha_state()

	@property
	def temperature_unit(self):
		"""The unit of measurement used by the platform."""
		return TEMP_CELSIUS


class LWRFThermostat(LWRFHeating):

	def __init__(self, heating):
		self._operation_list = ['Standby','Running','Away','Frost','Constant','Holiday','Error','Retrieving...']
		super(LWRFThermostat, self).__init__(heating)


	@property
	def icon(self):
		return "mdi:fire"

#    @property
#    def is_away_mode_on(self):
#        """Return if away mode is on."""
#        try:
#            if self._heating.state is "away":
#                return True
#            else:
#                return None
#        except AttributeError:
#            return None

	@property
	def current_operation(self):
		"""Return current operation ie. heat, cool, idle."""
		try:
			state = self._heating.state
		except AttributeError:
			return self._operation_list[7]

		if state == "stby":
			return self._operation_list[0]
		elif state == "run":
			return self._operation_list[1]
		elif state == "away":
			return self._operation_list[2]
		elif state == "frost":
			return self._operation_list[3]
		elif state == "comf":
			return self._operation_list[4]
		elif state == "hday":
			return self._operation_list[5]
		return self._operation_list[6]

	@property
	def operation_list(self):
		"""List of available operation modes."""
		return self._operation_list[:5]

	def set_operation_mode(self, operation_mode):
		"""Set new target temperature"""
		self._heating.set_mode(self._operation_list.index(operation_mode))
		state = "stby"
		if operation_mode == "Standby":
			state = "stby"
		elif operation_mode == "Running":
			state = "run"
		elif operation_mode == "Away":
			state = "away"
		elif operation_mode == "Frost":
			state = "frost"
		elif operation_mode == "Constant":
			state = "comf"
		elif operation_mode == "Holiday":
			state = "hday"
		self._heating.state = state
		self._heating.refresh()
		self.update_ha_state()

	@property
	def state(self):
		state = 'stby'
		try:
			state = self._heating.state
		except :
			pass
		if state is "stby":
			return self._operation_list[0]
		elif state is "run":
			return self._operation_list[1]
		elif state is "away":
			return self._operation_list[2]
		elif state is "frost":
			return self._operation_list[3]
		elif state is "comf":
			return self._operation_list[4]
		elif state is "hday":
			return self._operation_list[5]
		return self._operation_list[0]

#    def turn_away_mode_on(self):#
#        """Turn away mode on."""
#        self._heating.set_mode(2)
#        self.update_ha_state()

#    def turn_away_mode_off(self):
#        """Turn away mode off."""
#        self._heating.set_mode(1)
#        self.update_ha_state()
