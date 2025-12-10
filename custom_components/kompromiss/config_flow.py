"""Config flow for the Kompromiss integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    DOMAIN,
    CONF_SOT_NUMBER,
    CONF_TEMPERATURE_SENSORS,
    CONF_PRICE_SENSOR,
    CONF_LOWEST_TEMPERATURE,
    CONF_T_MAX,
    CONF_SOT_MIN,
    CONF_SOT_MAX,
    CONF_STEP_MINUTES,
    CONF_HORIZON_STEPS,
    CONF_ENABLED,
    DEFAULT_T_MIN,
    DEFAULT_T_MAX,
    DEFAULT_SOT_MIN,
    DEFAULT_SOT_MAX,
    DEFAULT_STEP_MINUTES,
    DEFAULT_HORIZON_STEPS,
    DEFAULT_ENABLED,
)


class KompromissConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Kompromiss."""

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        if user_input is not None:
            title = "Kompromiss"
            return self.async_create_entry(title=title, data=user_input)

        data_schema = vol.Schema(
            {
                vol.Required(CONF_SOT_NUMBER): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=["number"])
                ),
                vol.Required(CONF_TEMPERATURE_SENSORS): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        multiple=True, domain=["sensor"], device_class="temperature"
                    )
                ),
                vol.Required(CONF_PRICE_SENSOR): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=["sensor"])
                ),
                vol.Optional(CONF_LOWEST_TEMPERATURE, default=DEFAULT_T_MIN): vol.Coerce(float),
                vol.Optional(CONF_T_MAX, default=DEFAULT_T_MAX): vol.Coerce(float),
                vol.Optional(CONF_SOT_MIN, default=DEFAULT_SOT_MIN): vol.Coerce(float),
                vol.Optional(CONF_SOT_MAX, default=DEFAULT_SOT_MAX): vol.Coerce(float),
                vol.Optional(
                    CONF_STEP_MINUTES, default=DEFAULT_STEP_MINUTES
                ): vol.Coerce(int),
                vol.Optional(
                    CONF_HORIZON_STEPS, default=DEFAULT_HORIZON_STEPS
                ): vol.Coerce(int),
                vol.Optional(CONF_ENABLED, default=DEFAULT_ENABLED): bool,
            }
        )
        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return KompromissOptionsFlow(config_entry)

    def is_matching(self, other_flow) -> bool:
        return self == other_flow


class KompromissOptionsFlow(config_entries.OptionsFlow):
    """Options flow for Kompromiss."""

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
                    CONF_SOT_NUMBER, default=data.get(CONF_SOT_NUMBER)
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=["number"])
                ),
                vol.Required(
                    CONF_TEMPERATURE_SENSORS, default=data.get(CONF_TEMPERATURE_SENSORS)
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        multiple=True, domain=["sensor"], device_class="temperature"
                    )
                ),
                vol.Required(
                    CONF_PRICE_SENSOR, default=data.get(CONF_PRICE_SENSOR)
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=["sensor"])
                ),
                vol.Optional(
                    CONF_LOWEST_TEMPERATURE, default=data.get(CONF_LOWEST_TEMPERATURE, DEFAULT_T_MIN)
                ): vol.Coerce(float),
                vol.Optional(
                    CONF_T_MAX, default=data.get(CONF_T_MAX, DEFAULT_T_MAX)
                ): vol.Coerce(float),
                vol.Optional(
                    CONF_SOT_MIN, default=data.get(CONF_SOT_MIN, DEFAULT_SOT_MIN)
                ): vol.Coerce(float),
                vol.Optional(
                    CONF_SOT_MAX, default=data.get(CONF_SOT_MAX, DEFAULT_SOT_MAX)
                ): vol.Coerce(float),
                vol.Optional(
                    CONF_STEP_MINUTES,
                    default=data.get(CONF_STEP_MINUTES, DEFAULT_STEP_MINUTES),
                ): vol.Coerce(int),
                vol.Optional(
                    CONF_HORIZON_STEPS,
                    default=data.get(CONF_HORIZON_STEPS, DEFAULT_HORIZON_STEPS),
                ): vol.Coerce(int),
                vol.Optional(
                    CONF_ENABLED, default=data.get(CONF_ENABLED, DEFAULT_ENABLED)
                ): bool,
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
