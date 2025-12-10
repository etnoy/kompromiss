"""Sensor entity for the Kompromiss heat price optimizer."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant


async def async_setup_entry(
    _hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities
):
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
