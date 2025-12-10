"""Kompromiss component"""

import logging

from homeassistant.core import HomeAssistant, ServiceCall


DOMAIN = "kompromiss"
_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant) -> bool:
    """Set up the Kompromiss component."""

    def my_service(call: ServiceCall) -> None:
        """My first service."""
        _LOGGER.info("Received data: %s", call.data)

    hass.services.async_register(DOMAIN, "demo", my_service)

    return True
