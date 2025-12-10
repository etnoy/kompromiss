"""Kompromiss component"""

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from kompromiss import const

PLATFORMS: list[str] = ["switch", "sensor"]


async def async_setup() -> bool:
    """Set up the Kompromiss component."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[const.DOMAIN].pop(entry.entry_id, None)
    return unload_ok
