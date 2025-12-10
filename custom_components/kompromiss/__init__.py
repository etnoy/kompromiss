from homeassistant.core import HomeAssistant
from homeassistant.helpers.discovery import load_platform
from homeassistant.helpers.typing import ConfigType

DOMAIN = 'kompromiss'


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Kompromiss component."""    

    return True