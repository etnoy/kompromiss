"""Sensor entity for the Kompromiss heat price optimizer."""

from __future__ import annotations
import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from . import const

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities
):
    data = hass.data[const.DOMAIN][config_entry.entry_id]

    _LOGGER.debug("async_setup_entry: %s", data)

    async_add_entities([SimulatedOutdoorTemperatureSensor(config_entry)])


class SimulatedOutdoorTemperatureSensor(SensorEntity):
    """Sensor entity for the simulated outdoor temperature."""

    _attr_device_class = "temperature"
    _attr_native_unit_of_measurement = "°C"
    _attr_has_entity_name = True
    _attr_name = "Simulated Outdoor Temperature"

    @property
    def translation_key(self):
        return "simulated_outdoor_temperature"
