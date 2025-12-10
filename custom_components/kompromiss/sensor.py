"""Sensor entity for the Kompromiss heat price optimizer."""

from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant


async def async_setup_entry(
    _hass: HomeAssistant, _config_entry: ConfigEntry, async_add_entities
):
    """Set up the sensor platform."""
    async_add_entities([SimulatedOutdoorTemperatureSensor()])


class SimulatedOutdoorTemperatureSensor(SensorEntity):
    """Sensor entity for the simulated outdoor temperature, i.e. the temperature that is sent to the heat pump."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = "°C"
    _attr_has_entity_name = True
    _attr_name = "Simulated Outdoor Temperature"
    _attr_unique_id = "kompromiss_simulated_outdoor_temperature"

    @property
    def translation_key(self) -> str:
        """Return the translation key for the sensor."""
        return "simulated_outdoor_temperature"

    @property
    def native_value(self) -> float:
        """Return the current temperature value in Celsius."""
        return 20.0
