from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    DATA_COORDINATOR,
)
from .coordinator import KompromissCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
):
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: KompromissCoordinator = data[DATA_COORDINATOR]
    async_add_entities([HeatOptimizerStatusSensor(coordinator, entry)])


class HeatOptimizerStatusSensor(
    CoordinatorEntity[KompromissCoordinator], SensorEntity
):
    _attr_has_entity_name = True
    _attr_name = "Heat Optimizer Status"
    _attr_native_unit_of_measurement = "°C"
    _attr_icon = "mdi:thermometer"

    def __init__(self, coordinator: KompromissCoordinator, entry: ConfigEntry):
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_status"

    @property
    def native_value(self):
        data = self.coordinator.data or {}
        return data.get("sot")

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data or {}
        return {
            "virtual_temp": data.get("virtual_temp"),
            "coldest": data.get("coldest"),
            "hottest": data.get("hottest"),
            "prices": data.get("prices"),
            "temps": data.get("temps"),
            "enabled": data.get("enabled"),
        }
