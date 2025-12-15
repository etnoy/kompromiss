"""Sensor entity for the Kompromiss heat price optimizer."""

from __future__ import annotations
import logging
from typing import Final

from homeassistant.components.sensor import (
    EntityCategory,
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .controller import ControllerState, TemperatureController
from .device import ensure_device

from .const import (
    DOMAIN,
    ACTUAL_OUTDOOR_TEMPERATURE_SENSOR,
    INDOOR_TEMPERATURE_SENSOR,
)

_LOGGER: Final = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities
):
    device = ensure_device(hass, config_entry)
    controller = hass.data[DOMAIN][config_entry.entry_id]

    sensors = [
        SimulatedOutdoorTemperatureSensor(config_entry, device.id, controller),
        ActualOutdoorTemperatureSensor(config_entry, device.id),
        IndoorTemperatureSensor(config_entry, device.id),
        TemperatureOffsetSensor(config_entry, device.id, controller),
    ]
    async_add_entities(sensors)


class SimulatedOutdoorTemperatureSensor(SensorEntity):
    """Sensor entity for the simulated outdoor temperature, i.e. the temperature that is sent to the heat pump."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "°C"
    _attr_has_entity_name = True
    _attr_name = "Simulated Outdoor Temperature"
    _attr_unique_id = "kompromiss_simulated_outdoor_temperature"

    def __init__(
        self,
        config_entry: ConfigEntry,
        device_id: str,
        controller: TemperatureController,
    ):
        self._config_entry = config_entry
        self._device_id = device_id
        self._controller = controller
        self._temperature = None

    async def async_added_to_hass(self):
        self._controller.async_subscribe_sensor(self._on_temperature_update)
        return await super().async_added_to_hass()

    async def async_will_remove_from_hass(self):
        """Clean up when entity is removed."""

        self._controller.async_unsubscribe_sensor(self._on_temperature_update)
        return await super().async_will_remove_from_hass()

    def _on_temperature_update(self, state: ControllerState) -> None:
        """Callback when controller state changes."""
        self._temperature = state.simulated_outdoor_temperature
        self.schedule_update_ha_state()

    @property
    def device_info(self):
        return {"identifiers": {(DOMAIN, self._config_entry.entry_id)}}

    @property
    def native_value(self) -> float | None:
        return self._temperature

    @property
    def translation_key(self) -> str:
        return "simulated_outdoor_temperature"


class ActualOutdoorTemperatureSensor(SensorEntity):
    """Sensor entity for the measured outdoor temperature."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = "°C"
    _attr_has_entity_name = True
    _attr_name = "Actual Outdoor Temperature"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, config_entry: ConfigEntry, device_id: str):
        self._config_entry = config_entry
        self._device_id = device_id
        self._attr_unique_id = "kompromiss_actual_outdoor_temperature"

    @property
    def device_info(self):
        return {"identifiers": {(DOMAIN, self._config_entry.entry_id)}}

    @property
    def native_value(self) -> float | None:
        hass = self.hass
        if not hass:
            return None

        entity_id = self._config_entry.data.get(ACTUAL_OUTDOOR_TEMPERATURE_SENSOR)

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
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, config_entry: ConfigEntry, device_id: str):
        self._config_entry = config_entry
        self._device_id = device_id
        self._attr_unique_id = "kompromiss_indoor_temperature"

    @property
    def device_info(self):
        return {"identifiers": {(DOMAIN, self._config_entry.entry_id)}}

    @property
    def native_value(self) -> float | None:
        hass = self.hass
        if not hass:
            return None

        entity_id = self._config_entry.data.get(INDOOR_TEMPERATURE_SENSOR)
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
        return "indoor_temperature"


class TemperatureOffsetSensor(SensorEntity):
    """Sensor entity for the temperature offset applied to outdoor temperature."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = "°C"
    _attr_has_entity_name = True
    _attr_name = "Temperature Offset"
    _attr_unique_id = "kompromiss_temperature_offset"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        config_entry: ConfigEntry,
        device_id: str,
        controller: TemperatureController,
    ):
        self._config_entry = config_entry
        self._device_id = device_id
        self._controller = controller
        self._offset: float | None = None

    async def async_added_to_hass(self):
        self._controller.async_subscribe_sensor(self._on_temperature_update)
        return await super().async_added_to_hass()

    async def async_will_remove_from_hass(self):
        """Clean up when entity is removed."""
        self._controller.async_unsubscribe_sensor(self._on_temperature_update)
        return await super().async_will_remove_from_hass()

    def _on_temperature_update(self, state: ControllerState) -> None:
        """Callback when controller state changes."""
        self._offset = state.offset

        self.schedule_update_ha_state()

    @property
    def device_info(self):
        return {"identifiers": {(DOMAIN, self._config_entry.entry_id)}}

    @property
    def native_value(self) -> float | None:
        return self._offset

    @property
    def translation_key(self) -> str:
        return "temperature_offset"
