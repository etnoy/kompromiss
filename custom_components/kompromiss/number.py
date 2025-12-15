"""Number entity for the Kompromiss heat price optimizer."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .device import ensure_device

from .const import (
    DEFAULT_MINIMUM_INDOOR_TEMPERATURE,
    DEFAULT_MAXIMUM_INDOOR_TEMPERATURE,
    DOMAIN,
    SIGNAL_MPC_WEIGHT_TEMP_DEVIATION_CHANGED,
    SIGNAL_MPC_WEIGHT_COMFORT_VIOLATION_CHANGED,
)


STORAGE_KEY = "kompromiss_number_inputs"
STORAGE_VERSION = 1


async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities
):
    device = ensure_device(hass, config_entry)

    numbers = [
        MinimumIndoorTemperatureNumber(hass, config_entry, device.id),
        MaximumIndoorTemperatureNumber(hass, config_entry, device.id),
        WeightTemperatureDeviationNumber(hass, config_entry, device.id),
        WeightComfortBandViolationNumber(hass, config_entry, device.id),
    ]
    async_add_entities(numbers)


class MinimumIndoorTemperatureNumber(NumberEntity):
    """Number entity for the minimum indoor temperature."""

    _attr_has_entity_name = True
    _attr_name = "Minimum Indoor Temperature"
    _attr_native_unit_of_measurement = "°C"
    _attr_unique_id = "kompromiss_minimum_indoor_temperature"
    _attr_native_min_value = 5.0
    _attr_native_max_value = 50.0
    _attr_native_step = 0.1

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry, device_id: str):
        self._hass = hass
        self._config_entry = config_entry
        self._device_id = device_id
        self._store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._value = DEFAULT_MINIMUM_INDOOR_TEMPERATURE

    @property
    def device_info(self):
        return {"identifiers": {(DOMAIN, self._config_entry.entry_id)}}

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        data = await self._store.async_load()
        if data and "minimum" in data:
            self._value = data["minimum"]
        else:
            self._value = DEFAULT_MINIMUM_INDOOR_TEMPERATURE
        self.async_write_ha_state()

    @property
    def native_value(self) -> float:
        return self._value

    async def async_set_native_value(self, value: float) -> None:
        self._value = value
        data = await self._store.async_load() or {}
        data["minimum"] = value
        await self._store.async_save(data)
        self.async_write_ha_state()

    @property
    def translation_key(self) -> str:
        return "minimum_indoor_temperature"


class MaximumIndoorTemperatureNumber(NumberEntity):
    """Number entity for the maximum indoor temperature."""

    _attr_has_entity_name = True
    _attr_name = "Maximum Indoor Temperature"
    _attr_native_unit_of_measurement = "°C"
    _attr_unique_id = "kompromiss_maximum_indoor_temperature"
    _attr_native_min_value = 5.0
    _attr_native_max_value = 50.0
    _attr_native_step = 0.1

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry, device_id: str):
        self._hass = hass
        self._config_entry = config_entry
        self._device_id = device_id
        self._store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._value = DEFAULT_MAXIMUM_INDOOR_TEMPERATURE

    @property
    def device_info(self):
        return {"identifiers": {(DOMAIN, self._config_entry.entry_id)}}

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        data = await self._store.async_load()
        if data and "maximum" in data:
            self._value = data["maximum"]
        else:
            self._value = DEFAULT_MAXIMUM_INDOOR_TEMPERATURE
        self.async_write_ha_state()

    @property
    def native_value(self) -> float:
        return self._value

    async def async_set_native_value(self, value: float) -> None:
        self._value = value
        data = await self._store.async_load() or {}
        data["maximum"] = value
        await self._store.async_save(data)
        self.async_write_ha_state()

    @property
    def translation_key(self) -> str:
        return "maximum_indoor_temperature"


class WeightTemperatureDeviationNumber(NumberEntity):
    """Number entity for the MPC weight on temperature deviation from target."""

    _attr_has_entity_name = True
    _attr_name = "Weight Temperature Deviation"
    _attr_unique_id = "kompromiss_weight_temperature_deviation"
    _attr_native_min_value = 0.0
    _attr_native_max_value = 1000000.0
    _attr_native_step = 100.0
    _attr_mode = "box"

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry, device_id: str):
        self._hass = hass
        self._config_entry = config_entry
        self._device_id = device_id
        self._store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._value = 1000.0  # Default from MPCParameters

    @property
    def device_info(self):
        return {"identifiers": {(DOMAIN, self._config_entry.entry_id)}}

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        data = await self._store.async_load()
        if data and "weight_temperature_deviation" in data:
            self._value = data["weight_temperature_deviation"]
        else:
            self._value = 1000.0
        self.async_write_ha_state()

    @property
    def native_value(self) -> float:
        return self._value

    async def async_set_native_value(self, value: float) -> None:
        self._value = value
        data = await self._store.async_load() or {}
        data["weight_temperature_deviation"] = value
        await self._store.async_save(data)
        self.async_write_ha_state()
        # Notify subscribers of the change
        async_dispatcher_send(
            self._hass, SIGNAL_MPC_WEIGHT_TEMP_DEVIATION_CHANGED, value
        )

    @property
    def translation_key(self) -> str:
        return "weight_temperature_deviation"


class WeightComfortBandViolationNumber(NumberEntity):
    """Number entity for the MPC weight on comfort band violations."""

    _attr_has_entity_name = True
    _attr_name = "Weight Comfort Band Violation"
    _attr_unique_id = "kompromiss_weight_comfort_band_violation"
    _attr_native_min_value = 0.0
    _attr_native_max_value = 1000000.0
    _attr_native_step = 100.0
    _attr_mode = "box"

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry, device_id: str):
        self._hass = hass
        self._config_entry = config_entry
        self._device_id = device_id
        self._store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._value = 10000.0  # Default from MPCParameters

    @property
    def device_info(self):
        return {"identifiers": {(DOMAIN, self._config_entry.entry_id)}}

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        data = await self._store.async_load()
        if data and "weight_comfort_band_violation" in data:
            self._value = data["weight_comfort_band_violation"]
        else:
            self._value = 10000.0
        self.async_write_ha_state()

    @property
    def native_value(self) -> float:
        return self._value

    async def async_set_native_value(self, value: float) -> None:
        self._value = value
        data = await self._store.async_load() or {}
        data["weight_comfort_band_violation"] = value
        await self._store.async_save(data)
        self.async_write_ha_state()
        # Notify subscribers of the change
        async_dispatcher_send(
            self._hass, SIGNAL_MPC_WEIGHT_COMFORT_VIOLATION_CHANGED, value
        )

    @property
    def translation_key(self) -> str:
        return "weight_comfort_band_violation"
