from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from .const import DOMAIN


def ensure_device(hass: HomeAssistant, entry: ConfigEntry) -> dr.DeviceEntry:
    dev_reg = dr.async_get(hass)
    device = dev_reg.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.entry_id)},
        name="Kompromiss",
        manufacturer="Kompromiss",
    )
    return device
