"""Number entity for the Kompromiss heat price optimizer."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from . import const
from .device import ensure_device


STORAGE_KEY = "kompromiss_indoor_temperatures"
STORAGE_VERSION = 1


async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities
):
    device = ensure_device(hass, config_entry)

    numbers = [
        MinimumIndoorTemperatureNumber(hass, config_entry, device.id),
        MaximumIndoorTemperatureNumber(hass, config_entry, device.id),
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
        """Initialize the number entity."""
        self._hass = hass
        self._config_entry = config_entry
        self._device_id = device_id
        self._store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._value = const.DEFAULT_MINIMUM_INDOOR_TEMPERATURE

    @property
    def device_info(self):
        """Return device info to link entity to device."""
        return {"identifiers": {(const.DOMAIN, self._config_entry.entry_id)}}

    async def async_added_to_hass(self) -> None:
        """Load value from storage when added to hass."""
        await super().async_added_to_hass()
        data = await self._store.async_load()
        if data and "minimum" in data:
            self._value = data["minimum"]
        else:
            self._value = const.DEFAULT_MINIMUM_INDOOR_TEMPERATURE
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
        """Initialize the number entity."""
        self._hass = hass
        self._config_entry = config_entry
        self._device_id = device_id
        self._store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._value = const.DEFAULT_MAXIMUM_INDOOR_TEMPERATURE

    @property
    def device_info(self):
        return {"identifiers": {(const.DOMAIN, self._config_entry.entry_id)}}

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        data = await self._store.async_load()
        if data and "maximum" in data:
            self._value = data["maximum"]
        else:
            self._value = const.DEFAULT_MAXIMUM_INDOOR_TEMPERATURE
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
