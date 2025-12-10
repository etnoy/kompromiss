from homeassistant.config_entries import ConfigEntry, ConfigType
from homeassistant.core import HomeAssistant

from . import const


async def async_setup(hass: HomeAssistant, _config: ConfigType) -> bool:
    hass.data.setdefault(const.DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    hass.data.setdefault(const.DOMAIN, {})
    await hass.config_entries.async_forward_entry_setups(config_entry, const.PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(
        config_entry, const.PLATFORMS
    )
    if unload_ok:
        hass.data[const.DOMAIN].pop(config_entry.entry_id, None)
    return unload_ok
