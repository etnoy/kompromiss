from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    CONF_INDOOR_TEMPERATURE_SENSOR,
    PLATFORMS,
    DOMAIN,
    CONF_ACTUAL_OUTDOOR_TEMPERATURE_SENSOR,
    CONF_SIMULATED_OUTDOOR_TEMPERATURE_SENSOR,
)
from .controller import TemperatureController


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})

    actual_temp_entity_id = config_entry.data.get(
        CONF_ACTUAL_OUTDOOR_TEMPERATURE_SENSOR
    )
    simulated_temperature_entity_id = config_entry.data.get(
        CONF_SIMULATED_OUTDOOR_TEMPERATURE_SENSOR
    )
    indoor_temperature_entity_id = config_entry.data.get(CONF_INDOOR_TEMPERATURE_SENSOR)

    controller = TemperatureController(
        hass,
        actual_temp_entity_id,
        simulated_temperature_entity_id,
        indoor_temperature_entity_id,
    )

    await controller.async_subscribe()
    hass.data[DOMAIN][config_entry.entry_id] = controller

    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(
        config_entry, PLATFORMS
    )
    if unload_ok:
        controller = hass.data[DOMAIN].pop(config_entry.entry_id, None)
        if controller:
            controller.async_unsubscribe()
    return unload_ok
