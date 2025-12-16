from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    INDOOR_TEMPERATURE_SENSOR,
    PLATFORMS,
    DOMAIN,
    ACTUAL_OUTDOOR_TEMPERATURE_SENSOR,
)
from .controller import TemperatureController


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})

    actual_temp_entity_id = config_entry.data.get(ACTUAL_OUTDOOR_TEMPERATURE_SENSOR)
    indoor_temperature_entity_id = config_entry.data.get(INDOOR_TEMPERATURE_SENSOR)

    controller = TemperatureController(
        hass,
        actual_temp_entity_id,
        indoor_temperature_entity_id,
    )

    await controller.async_subscribe()

    # Apply initial parameters from options if they exist
    if config_entry.options:
        await controller.update_parameters_from_options(config_entry.options)

    hass.data[DOMAIN][config_entry.entry_id] = controller

    # Register options update listener
    config_entry.async_on_unload(
        config_entry.add_update_listener(async_options_updated)
    )

    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)
    return True


async def async_options_updated(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    """Handle options update.

    This is called when the user saves changes in the options flow.
    We update the controller parameters without reloading the integration.
    """
    controller = hass.data[DOMAIN].get(config_entry.entry_id)
    if controller:
        await controller.update_parameters_from_options(config_entry.options)


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(
        config_entry, PLATFORMS
    )
    if unload_ok:
        controller = hass.data[DOMAIN].pop(config_entry.entry_id, None)
        if controller:
            controller.async_unsubscribe()
    return unload_ok
