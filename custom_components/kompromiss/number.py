"""Number entity for the Kompromiss heat price optimizer."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from . import const

STORAGE_KEY = "kompromiss_indoor_temperatures"
STORAGE_VERSION = 1


async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities
):
    """Set up number entities from a config entry."""
    numbers = [
        MinimumIndoorTemperatureNumber(hass, config_entry),
        MaximumIndoorTemperatureNumber(hass, config_entry),
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

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry):
        self._hass = hass
        self._config_entry = config_entry
        self._store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._value = const.DEFAULT_MINIMUM_INDOOR_TEMPERATURE

    async def async_added_to_hass(self) -> None:
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

    def set_native_value(self, value: float) -> None:
        self._hass.async_create_task(self.async_set_native_value(value))

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

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry):
        """Initialize the number entity."""
        self._hass = hass
        self._config_entry = config_entry
        self._store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._value = const.DEFAULT_MAXIMUM_INDOOR_TEMPERATURE

    async def async_added_to_hass(self) -> None:
        """Load value from storage when added to hass."""
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

    def set_native_value(self, value: float) -> None:
        self._hass.async_create_task(self.async_set_native_value(value))

    @property
    def translation_key(self) -> str:
        return "maximum_indoor_temperature"
