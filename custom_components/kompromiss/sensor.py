"""Sensor entity for the Kompromiss heat price optimizer."""

from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from . import const


async def async_setup_entry(
    _hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities
):
    sensors = [
        SimulatedOutdoorTemperatureSensor(config_entry),
        ActualOutdoorTemperatureSensor(config_entry),
        IndoorTemperatureSensor(config_entry),
    ]
    async_add_entities(sensors)


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


class ActualOutdoorTemperatureSensor(SensorEntity):
    """Sensor entity for the measured outdoor temperature."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = "°C"
    _attr_has_entity_name = True
    _attr_name = "Actual Outdoor Temperature"

    def __init__(self, config_entry: ConfigEntry):
        """Initialize the sensor with the configured temperature sensor entity ID."""
        self._config_entry = config_entry
        self._attr_unique_id = "kompromiss_actual_outdoor_temperature"

    @property
    def native_value(self) -> float | None:
        """Return the value from the configured temperature sensor."""
        hass = self.hass
        if not hass:
            return None

        entity_id = self._config_entry.data.get(
            const.CONF_ACTUAL_OUTDOOR_TEMPERATURE_SENSOR
        )

        if not entity_id:
            return None

        state = hass.states.get(entity_id)
        if state is None:
            return None

        try:
            return float(state.state)
        except (ValueError, TypeError):
            return None

    @property
    def translation_key(self):
        return "actual_outdoor_temperature"


class IndoorTemperatureSensor(SensorEntity):
    """Sensor entity for the measured indoor temperature."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = "°C"
    _attr_has_entity_name = True
    _attr_name = "Indoor Temperature"

    @property
    def translation_key(self):
        return "indoor_temperature"
