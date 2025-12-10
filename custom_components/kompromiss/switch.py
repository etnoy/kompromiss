from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, DATA_COORDINATOR
from .coordinator import KompromissCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: KompromissCoordinator = data[DATA_COORDINATOR]
    async_add_entities([KompromissSwitch(coordinator, entry)])


class KompromissSwitch(SwitchEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator: KompromissCoordinator, entry: ConfigEntry):
        self._coordinator = coordinator
        self._entry = entry
        self._attr_name = "Heat Price Optimizer"
        self._attr_unique_id = f"{entry.entry_id}_switch"

    @property
    def is_on(self) -> bool:
        return self._coordinator.enabled

    async def async_turn_on(self, **kwargs):
        self._coordinator.enabled = True
        await self._coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs):
        self._coordinator.enabled = False
        await self._coordinator.async_request_refresh()

    @property
    def available(self) -> bool:
        return True
