"""Number entity for the Kompromiss heat price optimizer."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .device import ensure_device

from .const import (
    DOMAIN,
    DEFAULT_TARGET_TEMPERATURE,
    DEFAULT_MINIMUM_INDOOR_TEMPERATURE,
)


@dataclass
class NumberConfig:
    """Configuration for a number entity."""

    unique_id: str
    storage_key: str
    default_value: float
    min_value: float
    max_value: float
    step: float
    translation_key: str
    unit_of_measurement: str | None = None
    mode: str = "auto"
    signal_on_change: str | None = None


# Define all number entities here - easy to add new ones!
NUMBER_ENTITIES = [
    # Comfort targets
    NumberConfig(
        unique_id="kompromiss_target_temperature",
        storage_key="target_temperature",
        default_value=DEFAULT_TARGET_TEMPERATURE,
        min_value=5.0,
        max_value=50.0,
        step=0.1,
        translation_key="target_temperature",
        unit_of_measurement="°C",
    ),
    NumberConfig(
        unique_id="kompromiss_minimum_indoor_temperature",
        storage_key="minimum_indoor_temperature",
        default_value=DEFAULT_MINIMUM_INDOOR_TEMPERATURE,
        min_value=5.0,
        max_value=50.0,
        step=0.1,
        translation_key="minimum_indoor_temperature",
        unit_of_measurement="°C",
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    """Set up Kompromiss number entities."""
    device = ensure_device(hass, config_entry)

    numbers = [
        KompromissNumber(hass, config_entry, device.id, config)
        for config in NUMBER_ENTITIES
    ]
    async_add_entities(numbers)


class KompromissNumber(NumberEntity):
    """Number entity that reads/writes to config entry options."""

    _attr_has_entity_name = True

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        device_id: str,
        config: NumberConfig,
    ):
        """Initialize the number entity."""
        self._hass = hass
        self._config_entry = config_entry
        self._device_id = device_id
        self._config = config

        # Set class attributes from config
        self._attr_unique_id = config.unique_id
        self._attr_native_min_value = config.min_value
        self._attr_native_max_value = config.max_value
        self._attr_native_step = config.step
        self._attr_mode = config.mode
        if config.unit_of_measurement:
            self._attr_native_unit_of_measurement = config.unit_of_measurement

    @property
    def device_info(self):
        """Return device information."""
        return {"identifiers": {(DOMAIN, self._config_entry.entry_id)}}

    async def async_added_to_hass(self) -> None:
        """Run when entity is added to hass."""
        await super().async_added_to_hass()

        # Listen for options updates
        self.async_on_remove(
            self._config_entry.add_update_listener(self._async_update_listener)
        )

    @callback
    async def _async_update_listener(
        self,
        _hass: HomeAssistant,
        _config_entry: ConfigEntry,
    ) -> None:
        """Handle options update."""
        self.async_write_ha_state()

    @property
    def native_value(self) -> float:
        """Return the current value from config entry options."""
        return self._config_entry.options.get(
            self._config.storage_key, self._config.default_value
        )

    async def async_set_native_value(self, value: float) -> None:
        """Update the value in config entry options."""
        # Update the config entry options
        new_options = dict(self._config_entry.options)
        new_options[self._config.storage_key] = value

        self.hass.config_entries.async_update_entry(
            self._config_entry, options=new_options
        )

        self.async_write_ha_state()

        # Immediately update controller parameters
        controller = self.hass.data.get(DOMAIN, {}).get(self._config_entry.entry_id)
        if controller:
            await controller.update_parameters_from_options(new_options)

        # Send signal if configured (for backward compatibility)
        if self._config.signal_on_change:
            async_dispatcher_send(self._hass, self._config.signal_on_change, value)

    @property
    def translation_key(self) -> str:
        """Return the translation key."""
        return self._config.translation_key
