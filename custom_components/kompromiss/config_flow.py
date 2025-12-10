"""Config flow for the Kompromiss integration."""

from __future__ import annotations


import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import selector

from kompromiss import const


class ConfigFlowHandler(config_entries.ConfigFlow, domain=const.DOMAIN):
    """Handle a config flow for Kompromiss."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle a user initiated config flow."""
        if user_input is not None:
            return self.async_create_entry(title="Kompromiss", data=user_input)
        return self.async_show_form(step_id="user", data_schema=vol.Schema({}))

    def is_matching(self, other_flow) -> bool:
        return True


class OptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, entry: config_entries.ConfigEntry):
        self._entry = entry

    async def async_step_init(self, user_input=None):
        """Initialize options flow."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        data = {**self._entry.data, **(self._entry.options or {})}
        schema = vol.Schema(
            {
                vol.Required(
                    const.CONF_TEMPERATURE_SENSOR,
                    default=data.get(const.CONF_TEMPERATURE_SENSOR),
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=["sensor"], device_class="temperature"
                    )
                ),
                vol.Required(
                    const.CONF_ELECTRICITY_PRICE_SENSOR,
                    default=data.get(const.CONF_ELECTRICITY_PRICE_SENSOR),
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=["sensor"])
                ),
                vol.Optional(
                    const.CONF_MINIMUM_INDOOR_TEMPERATURE,
                    default=data.get(
                        const.CONF_MINIMUM_INDOOR_TEMPERATURE, const.DEFAULT_T_MIN
                    ),
                ): vol.Coerce(float),
                vol.Optional(
                    const.CONF_MAXIMUM_INDOOR_TEMPERATURE,
                    default=data.get(
                        const.CONF_MAXIMUM_INDOOR_TEMPERATURE, const.DEFAULT_T_MAX
                    ),
                ): vol.Coerce(float),
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
