"""Sensor entity for the Kompromiss heat price optimizer."""

from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from . import const
from .controller import SimulatedOutdoorTemperatureController
from .device import ensure_device


async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities
):
    device = ensure_device(hass, config_entry)

    sensors = [
        SimulatedOutdoorTemperatureSensor(config_entry, device.id),
        ActualOutdoorTemperatureSensor(config_entry, device.id),
        IndoorTemperatureSensor(config_entry, device.id),
        TemperatureOffsetSensor(config_entry, device.id),
        ElectricityPriceSensor(config_entry, device.id),
    ]
    async_add_entities(sensors)


class SimulatedOutdoorTemperatureSensor(SensorEntity):
    """Sensor entity for the simulated outdoor temperature, i.e. the temperature that is sent to the heat pump."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = "°C"
    _attr_has_entity_name = True
    _attr_name = "Simulated Outdoor Temperature"
    _attr_unique_id = "kompromiss_simulated_outdoor_temperature"

    def __init__(self, config_entry: ConfigEntry, device_id: str):
        self._config_entry = config_entry
        self._device_id = device_id
        self._controller: SimulatedOutdoorTemperatureController | None = None

    @property
    def device_info(self):
        return {"identifiers": {(const.DOMAIN, self._config_entry.entry_id)}}

    @property
    def native_value(self) -> float | None:
        hass = self.hass
        if not hass:
            return None

        entity_id = self._config_entry.data.get(
            const.CONF_ACTUAL_OUTDOOR_TEMPERATURE_SENSOR
        )

        if not entity_id:
            return None

        if self._controller is None:
            self._controller = SimulatedOutdoorTemperatureController(hass, entity_id)

        return self._controller.get_simulated_temperature()

    @property
    def translation_key(self) -> str:
        return "simulated_outdoor_temperature"


class ActualOutdoorTemperatureSensor(SensorEntity):
    """Sensor entity for the measured outdoor temperature."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = "°C"
    _attr_has_entity_name = True
    _attr_name = "Actual Outdoor Temperature"

    def __init__(self, config_entry: ConfigEntry, device_id: str):
        self._config_entry = config_entry
        self._device_id = device_id
        self._attr_unique_id = "kompromiss_actual_outdoor_temperature"

    @property
    def device_info(self):
        return {"identifiers": {(const.DOMAIN, self._config_entry.entry_id)}}

    @property
    def native_value(self) -> float | None:
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

    def __init__(self, config_entry: ConfigEntry, device_id: str):
        self._config_entry = config_entry
        self._device_id = device_id
        self._attr_unique_id = "kompromiss_indoor_temperature"

    @property
    def device_info(self):
        return {"identifiers": {(const.DOMAIN, self._config_entry.entry_id)}}

    @property
    def native_value(self) -> float | None:
        hass = self.hass
        if not hass:
            return None

        entity_id = self._config_entry.data.get(const.CONF_INDOOR_TEMPERATURE_SENSOR)
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

    def __init__(self, config_entry: ConfigEntry, device_id: str):
        self._config_entry = config_entry
        self._device_id = device_id

    @property
    def device_info(self):
        return {"identifiers": {(const.DOMAIN, self._config_entry.entry_id)}}

    @property
    def native_value(self) -> float:
        return SimulatedOutdoorTemperatureController.TEMPERATURE_OFFSET

    @property
    def translation_key(self) -> str:
        return "temperature_offset"


class ElectricityPriceSensor(SensorEntity):
    """Sensor entity for the current electricity price."""

    _attr_has_entity_name = True
    _attr_name = "Electricity Price"
    _attr_unique_id = "kompromiss_electricity_price"

    def __init__(self, config_entry: ConfigEntry, device_id: str):
        self._config_entry = config_entry
        self._device_id = device_id

    @property
    def device_info(self):
        return {"identifiers": {(const.DOMAIN, self._config_entry.entry_id)}}

    @property
    def native_value(self) -> float | None:
        hass = self.hass
        if not hass:
            return None

        entity_id = self._config_entry.data.get(
            const.CONF_ELECTRICITY_PRICE_SENSOR
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
    def translation_key(self) -> str:
        return "electricity_price"

