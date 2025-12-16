"""Sensor entities for the Kompromiss heat price optimizer."""

from __future__ import annotations
import logging
from typing import Final, Callable, Optional

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
    SIMULATED_OUTDOOR_TEMPERATURE_SENSOR,
    TEMPERATURE_OFFSET_SENSOR,
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
        ProjectedIndoorTemperatureSensor(config_entry, device.id, controller),
        ProjectedMediumTemperatureSensor(config_entry, device.id, controller),
        ProjectedThermalPowerSensor(config_entry, device.id, controller),
        TemperatureOffsetSensor(config_entry, device.id, controller),
        MPCComputationTimeSensor(config_entry, device.id, controller),
    ]
    async_add_entities(sensors)


class _BaseKompromissSensor(SensorEntity):
    """Base sensor with common device info and init fields."""

    def __init__(self, config_entry: ConfigEntry, device_id: str):
        self._config_entry = config_entry
        self._device_id = device_id

    @property
    def device_info(self):
        return {"identifiers": {(DOMAIN, self._config_entry.entry_id)}}


class _ControllerBoundSensor(_BaseKompromissSensor):
    """Sensor that binds to controller updates and extracts a value."""

    _extract_value: Callable[[ControllerState], Optional[float]]

    def __init__(
        self,
        config_entry: ConfigEntry,
        device_id: str,
        controller: TemperatureController,
    ):
        super().__init__(config_entry, device_id)
        self._controller = controller
        self._native_value: Optional[float] = None

    async def async_added_to_hass(self):
        self._controller.async_subscribe_sensor(self._on_update)
        return await super().async_added_to_hass()

    async def async_will_remove_from_hass(self):
        self._controller.async_unsubscribe_sensor(self._on_update)
        return await super().async_will_remove_from_hass()

    def _on_update(self, state: ControllerState) -> None:
        self._native_value = self._extract_value(state)
        self.schedule_update_ha_state()

    @property
    def native_value(self) -> float | None:
        return self._native_value


class _PassthroughEntitySensor(_BaseKompromissSensor):
    """Sensor that reads a numeric value from another HA entity."""

    _config_key: str

    @property
    def native_value(self) -> float | None:  # type: ignore[override]
        hass = self.hass
        if not hass:
            return None

        entity_id = self._config_entry.data.get(self._config_key)
        if not entity_id:
            return None

        state = hass.states.get(entity_id)
        if state is None:
            return None

        try:
            return float(state.state)
        except (ValueError, TypeError):
            return None


class SimulatedOutdoorTemperatureSensor(_ControllerBoundSensor):
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
        super().__init__(config_entry, device_id, controller)
        self._extract_value = (
            lambda s: s.simulated_outdoor_temperatures[0]["temperature"]
            if s.simulated_outdoor_temperatures
            else None
        )

    @property
    def translation_key(self) -> str:
        return SIMULATED_OUTDOOR_TEMPERATURE_SENSOR


class ActualOutdoorTemperatureSensor(_PassthroughEntitySensor):
    """Diagnostic sensor entity for the measured outdoor temperature."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = "°C"
    _attr_has_entity_name = True
    _attr_name = "Actual Outdoor Temperature"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, config_entry: ConfigEntry, device_id: str):
        super().__init__(config_entry, device_id)
        self._attr_unique_id = "kompromiss_actual_outdoor_temperature"
        self._config_key = ACTUAL_OUTDOOR_TEMPERATURE_SENSOR

    @property
    def translation_key(self):
        return ACTUAL_OUTDOOR_TEMPERATURE_SENSOR


class IndoorTemperatureSensor(_PassthroughEntitySensor):
    """Diagnostic sensor entity for the measured indoor temperature."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = "°C"
    _attr_has_entity_name = True
    _attr_name = "Indoor Temperature"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, config_entry: ConfigEntry, device_id: str):
        super().__init__(config_entry, device_id)
        self._attr_unique_id = "kompromiss_indoor_temperature"
        self._config_key = INDOOR_TEMPERATURE_SENSOR

    @property
    def translation_key(self):
        return INDOOR_TEMPERATURE_SENSOR


class ProjectedIndoorTemperatureSensor(_ControllerBoundSensor):
    """Diagnostic sensor for the MPC-projected indoor temperature trajectory."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "°C"
    _attr_has_entity_name = True
    _attr_name = "Projected Indoor Temperature"
    _attr_unique_id = "kompromiss_projected_indoor_temperature"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        config_entry: ConfigEntry,
        device_id: str,
        controller: TemperatureController,
    ):
        super().__init__(config_entry, device_id, controller)
        self._extract_value = (
            lambda s: (s.projected_indoor_temperature[0]["temperature"])[1]
            if s.projected_indoor_temperature
            else None
        )

        self._data: list[dict[str, any]] | None = None

    def _on_update(self, state: ControllerState) -> None:
        """Store full projection and extract next step value."""
        if not state.projected_indoor_temperature:
            self._native_value = None
            self.schedule_update_ha_state()
            return

        self._native_value = state.projected_indoor_temperature[0]["temperature"]

        self._data = state.projected_indoor_temperature

        self.schedule_update_ha_state()

    @property
    def extra_state_attributes(self) -> dict[str, any] | None:
        """Return all projected temperatures as attributes."""
        if not self._data:
            return None

        return {"data": self._data}

    @property
    def translation_key(self) -> str:
        return "projected_indoor_temperature"


class ProjectedMediumTemperatureSensor(_ControllerBoundSensor):
    """Diagnostic sensor for the MPC-projected medium temperature trajectory."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "°C"
    _attr_has_entity_name = True
    _attr_name = "Projected Medium Temperature"
    _attr_unique_id = "kompromiss_projected_medium_temperature"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        config_entry: ConfigEntry,
        device_id: str,
        controller: TemperatureController,
    ):
        super().__init__(config_entry, device_id, controller)
        self._extract_value = (
            lambda s: s.projected_medium_temperature[0]["temperature"]
            if s.projected_medium_temperature
            else None
        )

        self._data: list[dict[str, any]] | None = None

    def _on_update(self, state: ControllerState) -> None:
        """Store full projection and extract next step value."""
        if not state.projected_medium_temperature:
            self._native_value = None
            self.schedule_update_ha_state()
            return

        self._native_value = state.projected_medium_temperature[0]["temperature"]

        self._data = state.projected_medium_temperature

        self.schedule_update_ha_state()

    @property
    def extra_state_attributes(self) -> dict[str, any] | None:
        """Return all projected medium temperatures as attributes."""
        if not self._data:
            return None

        return {"data": self._data}

    @property
    def translation_key(self) -> str:
        return "projected_medium_temperature"


class ProjectedThermalPowerSensor(_ControllerBoundSensor):
    """Diagnostic sensor for the MPC-projected thermal power trajectory."""

    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "W"
    _attr_has_entity_name = True
    _attr_name = "Projected Thermal Power"
    _attr_unique_id = "kompromiss_projected_thermal_power"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        config_entry: ConfigEntry,
        device_id: str,
        controller: TemperatureController,
    ):
        super().__init__(config_entry, device_id, controller)
        self._extract_value = (
            lambda s: s.projected_thermal_power[0]["temperature"]
            if s.projected_thermal_power
            else None
        )

        self._data: list[dict[str, any]] | None = None

    def _on_update(self, state: ControllerState) -> None:
        """Store full projection and extract next step value."""
        if not state.projected_thermal_power:
            self._native_value = None
            self.schedule_update_ha_state()
            return

        self._native_value = state.projected_thermal_power[0]["temperature"]

        self._data = state.projected_thermal_power

        self.schedule_update_ha_state()

    @property
    def extra_state_attributes(self) -> dict[str, any] | None:
        """Return all projected thermal power values as attributes."""
        if not self._data:
            return None

        return {"data": self._data}

    @property
    def translation_key(self) -> str:
        return "projected_thermal_power"


class TemperatureOffsetSensor(_ControllerBoundSensor):
    """Diagnostic sensor entity for the temperature offset applied to outdoor temperature."""

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
        super().__init__(config_entry, device_id, controller)
        self._extract_value = (
            lambda s: s.outdoor_temperature_offsets[0]["temperature"]
            if s.outdoor_temperature_offsets
            else None
        )

    @property
    def translation_key(self) -> str:
        return TEMPERATURE_OFFSET_SENSOR


class MPCComputationTimeSensor(_ControllerBoundSensor):
    """Diagnostic sensor for MPC optimization computation time."""

    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = "ms"
    _attr_has_entity_name = True
    _attr_name = "MPC Computation Time"
    _attr_unique_id = "kompromiss_mpc_computation_time"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        config_entry: ConfigEntry,
        device_id: str,
        controller: TemperatureController,
    ):
        super().__init__(config_entry, device_id, controller)
        self._extract_value = lambda s: s.computation_time

    @property
    def translation_key(self) -> str:
        return "mpc_computation_time"
