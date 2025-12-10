"""Config flow for the Kompromiss integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow

from homeassistant.helpers import selector

from .const import (
    DOMAIN,
    CONF_ACTUAL_OUTDOOR_TEMPERATURE_SENSOR,
    CONF_INDOOR_TEMPERATURE_SENSOR,
    CONF_ELECTRICITY_PRICE_SENSOR,
)


class ConfigFlowHandler(ConfigFlow, domain=DOMAIN):
    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            return self.async_create_entry(title="Kompromiss", data=user_input)

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_ACTUAL_OUTDOOR_TEMPERATURE_SENSOR,
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=["sensor"], device_class="temperature"
                    )
                ),
                vol.Required(
                    CONF_INDOOR_TEMPERATURE_SENSOR,
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=["sensor"], device_class="temperature"
                    )
                ),
                vol.Required(
                    CONF_ELECTRICITY_PRICE_SENSOR,
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=["sensor"])
                ),
            }
        )

        return self.async_show_form(step_id="user", data_schema=schema)

    def is_matching(self, other_flow) -> bool:
        return True
