"""Sensor entity for the Kompromiss heat price optimizer."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry


async def async_setup_entry(entry: ConfigEntry, async_add_entities):
    """Set up the Kompromiss status sensor entity."""
    async_add_entities([SimulatedOutdoorTemperatureSensor(entry)])


class SimulatedOutdoorTemperatureSensor(SensorEntity):
    _attr_device_class = "temperature"
    _attr_native_unit_of_measurement = "°C"
    _attr_has_entity_name = True
    _attr_name = "Simulated Outdoor Temperature"

    @property
    def translation_key(self):
        return "simulated_outdoor_temperature"
