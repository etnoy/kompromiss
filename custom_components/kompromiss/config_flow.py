"""Config flow for the Kompromiss integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlow, OptionsFlow

from homeassistant.helpers import selector

from . import const


class ConfigFlowHandler(ConfigFlow, domain=const.DOMAIN):
    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            return self.async_create_entry(title="Kompromiss", data=user_input)

        schema = vol.Schema(
            {
                vol.Required(
                    const.CONF_ACTUAL_OUTDOOR_TEMPERATURE_SENSOR,
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=["sensor"], device_class="temperature"
                    )
                ),
                vol.Required(
                    const.CONF_INDOOR_TEMPERATURE_SENSOR,
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=["sensor"], device_class="temperature"
                    )
                ),
                vol.Required(
                    const.CONF_ELECTRICITY_PRICE_SENSOR,
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=["sensor"])
                ),
            }
        )

        return self.async_show_form(step_id="user", data_schema=schema)

    def is_matching(self, other_flow) -> bool:
        return True


class OptionsFlowHandler(OptionsFlow):
    def __init__(self, entry: config_entries.ConfigEntry):
        self._entry = entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        data = {**self._entry.data, **(self._entry.options or {})}
        schema = vol.Schema(
            {
                vol.Optional(
                    const.CONF_LOWEST_SIMULATED_TEMPERATURE,
                    default=data.get(
                        const.CONF_LOWEST_SIMULATED_TEMPERATURE,
                        const.DEFAULT_LOWEST_SIMULATED_TEMPERATURE,
                    ),
                ): vol.Coerce(float),
                vol.Optional(
                    const.CONF_HIGHEST_SIMULATED_TEMPERATURE,
                    default=data.get(
                        const.CONF_HIGHEST_SIMULATED_TEMPERATURE,
                        const.DEFAULT_HIGHEST_SIMULATED_TEMPERATURE,
                    ),
                ): vol.Coerce(float),
                vol.Optional(
                    const.CONF_STEP_MINUTES,
                    default=data.get(
                        const.CONF_STEP_MINUTES, const.DEFAULT_STEP_MINUTES
                    ),
                ): vol.Coerce(int),
                vol.Optional(
                    const.CONF_HORIZON_STEPS,
                    default=data.get(
                        const.CONF_HORIZON_STEPS, const.DEFAULT_HORIZON_STEPS
                    ),
                ): vol.Coerce(int),
                vol.Optional(
                    const.CONF_ENABLED,
                    default=data.get(const.CONF_ENABLED, const.DEFAULT_ENABLED),
                ): bool,
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)


async def async_get_options_flow(
    config_entry: config_entries.ConfigEntry,
) -> OptionsFlowHandler:
    """Get the options flow for Kompromiss."""
    return OptionsFlowHandler(config_entry)
